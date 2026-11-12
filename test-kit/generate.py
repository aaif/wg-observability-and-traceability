#!/usr/bin/env python3
"""Rebuild every fixture in test-kit/cases/ from a fixed seed.

The records are synthetic OTLP/JSON trace exports for the support workflow in
the execution plan: an agent proposes creating a ticket (action P1), the action
executes, and an independently instrumented test service records the creation
and issues a signed receipt. The test service's signing key is derived from a
published seed, so the fixtures are reproducible byte for byte and the key
protects nothing. Ed25519 signatures are deterministic, so a rebuild on any
machine yields the same bytes, and CI checks that it does.

Attribute names are illustrative fixture identities, not proposed OTel
attribute names, the same convention issue #41 states for its example.

Run: python3 test-kit/generate.py            rewrite the fixtures
     python3 test-kit/generate.py --check    exit 1 if a rebuild would change any file
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

KIT = Path(__file__).resolve().parent
CASES = KIT / "cases"
TRUST = KIT / "trust"

#: Published on purpose: this key signs synthetic receipts and nothing else.
SEED = hashlib.sha256(b"aaif-wg-ot test-kit test-ticket-service key v1").digest()
SERVICE = "test-ticket-service"
AGENT = "support-agent"
TRACE = "5b8efff798038103d269b633813fc60c"
START = 1790000000000000000  # nanoseconds; fixed so the records never change


def _key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(SEED)


def _attrs(values: dict) -> list[dict]:
    out = []
    for k, v in values.items():
        if isinstance(v, bool):
            out.append({"key": k, "value": {"boolValue": v}})
        elif isinstance(v, int):
            out.append({"key": k, "value": {"intValue": str(v)}})
        else:
            out.append({"key": k, "value": {"stringValue": v}})
    return out


def _span(span_id: str, parent: str, name: str, offset_ms: int, attrs: dict) -> dict:
    start = START + offset_ms * 1_000_000
    return {
        "traceId": TRACE,
        "spanId": span_id,
        "parentSpanId": parent,
        "name": name,
        "kind": 1,
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(start + 5_000_000),
        "attributes": _attrs(attrs),
    }


def receipt_payload(fields: dict) -> bytes:
    """The bytes the test service signs: its fields as sorted, compact JSON."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()


def _receipt(span_id: str, offset_ms: int, receipt_id: str, *, tamper: bool = False,
             ticket_id: str = "T-1042") -> dict:
    fields = {
        "action_id": "P1",
        "created_at": "2026-09-21T15:00:00Z",
        "receipt_id": receipt_id,
        "service": SERVICE,
        "ticket_id": ticket_id,
    }
    signed = dict(fields, ticket_id="T-9999") if tamper else fields
    signature = base64.b64encode(_key().sign(receipt_payload(signed))).decode()
    return _span(span_id, "", "ticket.create.receipt", offset_ms, {
        "receipt.id": receipt_id,
        "receipt.action_id": fields["action_id"],
        "receipt.ticket_id": fields["ticket_id"],
        "receipt.created_at": fields["created_at"],
        "receipt.service": fields["service"],
        "receipt.signature": signature,
    })


def _agent_spans(claimed_verified: bool) -> list[dict]:
    """The agent's own spans. Identical in every case, including the producer's claim."""
    return [
        _span("0000000000000001", "", "invoke_agent", 0, {"conversation.id": "C1", "turn.id": "T1"}),
        _span("0000000000000002", "0000000000000001", "propose_action", 100, {
            "action.id": "P1", "action.intent": "create ticket for delayed order",
        }),
        _span("0000000000000003", "0000000000000001", "execute_tool create_ticket", 300, {
            "action.id": "P1",
            "tool.name": "create_ticket",
            "evidence.externally_verified": claimed_verified,
        }),
    ]


def _export(agent: list[dict], service: list[dict], *, tenant: str | None = None) -> dict:
    def block(name: str, spans: list[dict]) -> dict:
        resource = {"service.name": name}
        if tenant is not None:
            resource["tenant.id"] = tenant
        return {
            "resource": {"attributes": _attrs(resource)},
            "scopeSpans": [{"scope": {"name": "aaif-test-kit"}, "spans": spans}],
        }
    blocks = [block(AGENT, agent)]
    if service:
        blocks.append(block(SERVICE, service))
    return {"resourceSpans": blocks}


ISSUE_42 = {
    "document": "Trace model: build shared tests and a contribution template (issue #42)",
    "section": "the example in the issue body",
    "url": "https://github.com/aaif/wg-observability-and-traceability/issues/42",
    "also_stated_in": {
        "document": "Agent Behavior Trace Model shared contract, v0.7-draft (pull request #51)",
        "section": "6. Interpretation rules, Effects",
        "url": "https://github.com/aaif/wg-observability-and-traceability/blob/"
        "e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md",
    },
}
DEEP_DIVE_3_3 = {
    "document": "Agent to MCP Server boundary deep dive (pull request #32)",
    "section": "3.3 Evidence grades are established by the consumer, not the producer",
    "url": "https://github.com/aaif/wg-observability-and-traceability/blob/"
    "41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md",
    "outside": {
        "document": "Agent Behavior Trace Model shared contract, v0.7-draft (pull request #51)",
        "why": "section 6 treats a service-side receipt as correlation evidence, not cryptographic "
        "attestation; the signature check is outside v0.7-draft",
    },
}
SCOPED_EFFECTS = {
    "document": "Agent Behavior Trace Model shared contract, v0.7-draft (pull request #51)",
    "section": "3. Identity rules, rule 4; 6. Interpretation rules, Effects",
    "url": "https://github.com/aaif/wg-observability-and-traceability/blob/"
    "e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md",
}


def _basis(answer_follows: dict, checks: list[str], tenant: str | None = None) -> dict:
    """Name the rule and checks before a reader opens expected.json."""
    basis = {"answer_follows": answer_follows, "checks": checks,
             "evaluation_context": {"action": "P1", "service": SERVICE, "tenant": tenant}}
    if "receipt_signature" in checks:
        basis["effect_correlation_follows"] = ISSUE_42
    return basis


def build() -> dict[Path, bytes]:
    """Every file this script owns, keyed by path, as the bytes it should hold."""
    cases = {
        "effects-receipt-delivered-twice": (
            _export(_agent_spans(True), [_receipt("00000000000000a1", 400, "R-1"),
                                         _receipt("00000000000000a2", 900, "R-1")]),
            {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1042"]},
            ISSUE_42,
            ["effect_correlation"],
        ),
        "effects-receipt-missing": (
            _export(_agent_spans(True), []),
            {"action": "P1", "effect": "unconfirmed", "confirmed_tickets": None},
            ISSUE_42,
            ["effect_correlation"],
        ),
        "effects-ticket-id-changed": (
            _export(_agent_spans(True),
                    [_receipt("00000000000000c1", 400, "R-9", ticket_id="T-2088")]),
            {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-2088"]},
            ISSUE_42,
            ["effect_correlation"],
        ),
        "effects-action-id-reused-in-another-scope": (
            {"resourceSpans": (
                _export(_agent_spans(True), [_receipt("00000000000000d1", 400, "R-9")],
                        tenant="tenant-a")["resourceSpans"]
                + _export(_agent_spans(True),
                          [_receipt("00000000000000d2", 400, "R-9", ticket_id="T-2088")],
                          tenant="tenant-b")["resourceSpans"]
            )},
            {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1042"]},
            SCOPED_EFFECTS,
            ["effect_correlation"],
        ),
        "evidence-grade-pair-verifies": (
            _export(_agent_spans(True), [_receipt("00000000000000b1", 400, "R-7")]),
            {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1042"],
             "receipt_signature_verified": True},
            DEEP_DIVE_3_3,
            ["effect_correlation", "receipt_signature"],
        ),
        "evidence-grade-pair-fails": (
            _export(_agent_spans(True), [_receipt("00000000000000b1", 400, "R-7", tamper=True)]),
            {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1042"],
             "receipt_signature_verified": False},
            DEEP_DIVE_3_3,
            ["effect_correlation", "receipt_signature"],
        ),
    }
    files: dict[Path, bytes] = {}
    for name, (records, expected, follows, checks) in cases.items():
        files[CASES / name / "records.otlp.json"] = (json.dumps(records, indent=2) + "\n").encode()
        files[CASES / name / "expected.json"] = (json.dumps(expected, indent=2) + "\n").encode()
        tenant = "tenant-a" if name == "effects-action-id-reused-in-another-scope" else None
        files[CASES / name / "basis.json"] = (
            json.dumps(_basis(follows, checks, tenant), indent=2) + "\n").encode()
    public = _key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    files[TRUST / f"{SERVICE}.pub.pem"] = public
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the test-kit fixtures from a fixed seed.")
    parser.add_argument("--check", action="store_true",
                        help="change nothing; exit 1 if a rebuild would change any file")
    args = parser.parse_args()
    stale = []
    for path, data in build().items():
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                stale.append(path.relative_to(KIT))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if stale:
        print("generate: these files differ from a rebuild: "
              + ", ".join(str(p) for p in stale), file=sys.stderr)
        return 1
    print("generate: fixtures " + ("match a rebuild." if args.check else "written."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
