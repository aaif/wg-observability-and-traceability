#!/usr/bin/env python3
"""Answer each case's question from its exported records and compare with expected.json.

Every case under test-kit/cases/ holds an OTLP/JSON trace export and the answer a
correct reader must derive from it. Two readers ship here:

- `reference` derives everything from the records and the external party's key.
  It counts a ticket as created only on a receipt the test service signed,
  counts one receipt id once however often it is delivered, and reports a
  missing receipt as `unconfirmed`, never as "not created".
- `naive` reads the answer off what the producer wrote: it counts receipt spans
  and repeats the agent's own `evidence.externally_verified` claim. It exists to
  be wrong. `--reader naive --expect-fail` passes only when the naive reader
  gets every case marked `discriminates` wrong, which is what shows the fixtures
  can tell a reader that re-derives from one that repeats.

Run: python3 test-kit/run.py
     python3 test-kit/run.py --reader naive --expect-fail
Exit 0 as expected, 1 a case came out wrong (or, with --expect-fail, right),
2 the run could not happen.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key

KIT = Path(__file__).resolve().parent
CASES = KIT / "cases"
TRUST = KIT / "trust"
SERVICE = "test-ticket-service"

#: Cases the naive reader must get wrong. Each exists to separate a reader that
#: re-derives from one that repeats the producer, so a naive pass is a fixture defect.
DISCRIMINATES = (
    "effects-receipt-delivered-twice",
    "effects-receipt-missing",
    "evidence-grade-pair-fails",
)


def _value(attr: dict):
    v = attr["value"]
    for kind in ("stringValue", "boolValue"):
        if kind in v:
            return v[kind]
    if "intValue" in v:
        return int(v["intValue"])
    raise ValueError(f"unsupported attribute value {v!r}")


def spans(export: dict) -> list[tuple[str, dict]]:
    """(service.name, attributes) for every span in an OTLP/JSON export."""
    out = []
    for block in export.get("resourceSpans", []):
        res = {a["key"]: _value(a) for a in block.get("resource", {}).get("attributes", [])}
        for scope in block.get("scopeSpans", []):
            for span in scope.get("spans", []):
                attrs = {a["key"]: _value(a) for a in span.get("attributes", [])}
                out.append((res.get("service.name", ""), dict(attrs, _name=span["name"])))
    return out


def receipt_payload(fields: dict) -> bytes:
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()


def _verifies(key, attrs: dict) -> bool:
    fields = {
        "action_id": attrs.get("receipt.action_id"),
        "created_at": attrs.get("receipt.created_at"),
        "receipt_id": attrs.get("receipt.id"),
        "service": attrs.get("receipt.service"),
        "ticket_id": attrs.get("receipt.ticket_id"),
    }
    try:
        key.verify(base64.b64decode(attrs.get("receipt.signature", "")), receipt_payload(fields))
    except (InvalidSignature, ValueError):
        return False
    return True


def reference(export: dict, action: str, key) -> dict:
    receipts = [a for svc, a in spans(export)
                if svc == SERVICE and a.get("receipt.action_id") == action]
    verified = {a["receipt.id"]: a["receipt.ticket_id"] for a in receipts if _verifies(key, a)}
    if not verified:
        return {"action": action, "effect": "unconfirmed", "confirmed_tickets": None,
                "externally_verified": False}
    return {"action": action, "effect": "confirmed",
            "confirmed_tickets": sorted(set(verified.values())), "externally_verified": True}


def naive(export: dict, action: str, _key) -> dict:
    receipts = [a for _svc, a in spans(export) if a.get("receipt.action_id") == action]
    claimed = any(a.get("evidence.externally_verified") for _svc, a in spans(export)
                  if a.get("action.id") == action)
    return {"action": action, "effect": "confirmed" if claimed else "not created",
            "confirmed_tickets": [a["receipt.ticket_id"] for a in receipts] or [],
            "externally_verified": claimed}


READERS = {"reference": reference, "naive": naive}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the test-kit cases through a reader.")
    parser.add_argument("--reader", choices=sorted(READERS), default="reference")
    parser.add_argument("--expect-fail", action="store_true",
                        help="pass only if the reader gets every discriminating case wrong")
    args = parser.parse_args()
    try:
        key = load_pem_public_key((TRUST / f"{SERVICE}.pub.pem").read_bytes())
        names = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    except (OSError, ValueError) as exc:
        print(f"run: could not load the kit ({exc}); nothing was checked.", file=sys.stderr)
        return 2
    if not names:
        print("run: no cases found; nothing was checked.", file=sys.stderr)
        return 2
    reader = READERS[args.reader]
    wrong = []
    for name in names:
        case = CASES / name
        expected = json.loads((case / "expected.json").read_text())
        got = reader(json.loads((case / "records.otlp.json").read_text()), expected["action"], key)
        ok = got == expected
        print(f"{'ok  ' if ok else 'DIFF'} {name}" + ("" if ok else f"\n     expected {expected}\n     got      {got}"))
        if not ok:
            wrong.append(name)
    if args.expect_fail:
        missed = [n for n in DISCRIMINATES if n not in wrong]
        if missed:
            print(f"run: the {args.reader} reader answered {', '.join(missed)} correctly, so "
                  "those cases do not separate it from the reference reader.", file=sys.stderr)
            return 1
        print(f"run: the {args.reader} reader fails every discriminating case, as it must.")
        return 0
    print(f"run: {len(names) - len(wrong)} of {len(names)} cases answered as expected.")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
