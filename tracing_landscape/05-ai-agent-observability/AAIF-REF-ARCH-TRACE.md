# AAIF Reference Architecture: TRACE

| Field | Value |
|-------|-------|
| **Subject** | [TRACE (Trust, Runtime Attestation, and Compliance Evidence)](https://github.com/agentrust-io/trace-spec) |
| **Version** | 0.2 — Draft |
| **Date** | 2026-08-17 |

---

## Objective

Reference architecture for TRACE, an open specification for hardware-attested AI agent governance records that binds what executed, where, under which policy, touching which data class, calling which tools — into a single signed artifact rooted in silicon attestation and verifiable offline by any third party.

---

## Scope / Zoom Level

**System layer — cryptographic governance evidence spanning the full execution lifecycle.** TRACE operates above the observability layer: it does not produce telemetry (traces, metrics, logs) but rather produces *cryptographic proof* that a governed execution occurred. It consumes attestation evidence from hardware (TEE quotes), identity from SPIFFE/DID, provenance from SLSA, policy from Cedar/OPA, and anchors to transparency logs (SCITT). The Trust Record is the portable artifact a third party verifies without trusting the operator.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| TRACE Specification | v0.2 | Normative spec (Community Specification License 1.0) |
| agentrust-trace SDK | 0.6.0 | Python reference library (Apache 2.0) |
| Python | ≥3.10 | Runtime for SDK |
| cryptography | ≥41.0 | Ed25519 signing/verification |
| rfc8785 | ≥0.1 | JSON Canonicalization Scheme (JCS) |
| jsonschema | ≥4.0 | Schema validation |
| pydantic | ≥2.0 | TrustRecord model |
| cMCP (reference impl) | Latest | TEE gateway for MCP tool calls |
| Cedar policy engine | ≥3.0 | Policy evaluation inside TEE (via cMCP/AGT) |
| SCITT-compatible log | draft-22 | Transparency anchoring (Level 2) |
| Hardware TEE (Level 1+) | AMD SEV-SNP / Intel TDX / NVIDIA H100 / TPM2 | Silicon root of trust |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AI Agent Execution Environment                                 │
│                                                                                 │
│  ┌───────────────────────┐     ┌─────────────────────────────────────────────┐  │
│  │  Agent Framework      │     │  cMCP Gateway (TEE boundary)                │  │
│  │  (LangGraph, CrewAI,  │     │                                             │  │
│  │   AutoGen, raw Python)│     │  ┌────────────────────┐                     │  │
│  │                       │────►│  │ Cedar Policy Engine │                     │  │
│  │  MCP / A2A tool calls │     │  │ (allow/deny/escalate)                    │  │
│  └───────────────────────┘     │  └────────────────────┘                     │  │
│                                │  ┌────────────────────┐                     │  │
│                                │  │ Tool Transcript    │                     │  │
│                                │  │ (hash-bound)       │                     │  │
│                                │  └────────────────────┘                     │  │
│                                │  ┌────────────────────┐                     │  │
│                                │  │ Record Signing      │                     │  │
│                                │  │ (TEE-bound key)     │                     │  │
│                                │  └─────────┬──────────┘                     │  │
│                                └────────────┼────────────────────────────────┘  │
└─────────────────────────────────────────────┼───────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       TRACE Trust Record (Signed Artifact)                        │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  EAT Envelope (RFC 9711, JWT or CBOR-COSE)                               │   │
│  │  eat_profile: "tag:agentrust-io.com,2026:trace-v0.2"                     │   │
│  │                                                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │ subject  │  │  model   │  │ runtime  │  │  policy  │  │data_class│  │   │
│  │  │SPIFFE/DID│  │provider  │  │platform  │  │bundle_   │  │confidenti│  │   │
│  │  │          │  │model_id  │  │measure-  │  │hash      │  │al/public/│  │   │
│  │  │          │  │weights_  │  │ment      │  │enforce-  │  │restricted│  │   │
│  │  │          │  │digest    │  │rim_uri   │  │ment_mode │  │          │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────────┐  │   │
│  │  │tool_transcript│  │build_        │  │ appraisal│  │ transparency   │  │   │
│  │  │hash           │  │provenance    │  │ (EAR)    │  │ (SCITT receipt)│  │   │
│  │  │call_count     │  │slsa_level    │  │status    │  │ Level 2 only   │  │   │
│  │  │transcript_uri │  │builder       │  │verifier  │  │                │  │   │
│  │  │               │  │digest        │  │          │  │                │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────┘  └────────────────┘  │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────┐  ┌──────────────────────────────────┐  │   │
│  │  │  delegation  │  │   cnf    │  │          signature               │  │   │
│  │  │ (A2A DAG)    │  │(TEE key) │  │  Ed25519 over JCS canonical form │  │   │
│  │  │parent_record │  │jwk:{kty, │  │  of record sans signature field  │  │   │
│  │  │credential_id │  │ crv, x}  │  │                                  │  │   │
│  │  └──────────────┘  └──────────┘  └──────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────┬────────────────────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
┌─────────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐
│  Offline Verifier       │  │  SCITT Transparency   │  │  Relying Party          │
│                         │  │  Log                  │  │                         │
│  1. Parse envelope      │  │  • Append-only        │  │  • Browser extension    │
│  2. Resolve public key  │  │  • Inclusion proof    │  │  • CLI audit tool       │
│  3. Verify signature    │  │  • Public query       │  │  • Compliance dashboard │
│  4. Check EAT profile   │  │  • Receipt URI        │  │  • Cedar policy gate    │
│  5. Appraise claims     │  │                       │  │                         │
│  6. Check revocation    │  │                       │  │                         │
│     (optional, online)  │  │                       │  │                         │
└─────────────────────────┘  └───────────────────────┘  └─────────────────────────┘

                    Standards Composed (not replaced)
┌─────────────────────────────────────────────────────────────────────────────────┐
│  RATS/EAT (RFC 9711)  │  SLSA v1.0  │  SPIFFE  │  SCITT  │  EAR  │  MCP/A2A  │
│  Envelope + claims    │  Build prov │ Identity │ Anchor  │Appraise│ Tool calls │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

TRACE does not instrument in the observability sense — it produces *governance evidence*. The Trust Record binds together answers to five questions:

| Question | Record Field | What It Proves |
|----------|-------------|----------------|
| What model ran? | `model` (provider, model_id, weights_digest) | Specific model version executed |
| Where did it run? | `runtime` (platform, measurement, rim_uri) | Hardware environment identity |
| Under which policy? | `policy` (bundle_hash, enforcement_mode) | Policy in force at execution time |
| What data class was touched? | `data_class` | Sensitivity classification of I/O |
| Which tools were called? | `tool_transcript` (hash, call_count) | Cryptographic commitment to tool invocations |

Plus provenance (`build_provenance`), appraisal (`appraisal`), identity (`subject`), and optional anchoring (`transparency`).

### The Mechanism

**Record Production (cMCP reference path):**

1. Agent issues MCP tool call to cMCP gateway
2. Gateway evaluates Cedar policy inside TEE (allow/deny/escalate)
3. If allowed, forwards to upstream MCP server, captures transcript
4. At session end, assembles Trust Record fields from execution state
5. Computes SHA-256/SHA-384 of policy bundle, tool transcript, and workload binary
6. Signs record with TEE-bound Ed25519 key over RFC 8785 canonical JSON
7. Optionally submits to SCITT transparency log, appends receipt URI, re-signs

**Record Production (SDK-only path):**

```python
from agentrust_trace import TrustRecord, sign_record, load_signing_key

record = TrustRecord(
    eat_profile="tag:agentrust-io.com,2026:trace-v0.2",
    iat=int(time.time()),
    subject="spiffe://trust.example.org/agent/payments-processor",
    model=ModelInfo(provider="anthropic", model_id="claude-sonnet-4-6"),
    runtime=RuntimeInfo(platform="software-only", measurement="sha256:" + "0"*64),
    policy=PolicyInfo(bundle_hash="sha256:b2c3...", enforcement_mode="enforce"),
    data_class="confidential",
    build_provenance=BuildProvenance(slsa_level=1, digest="sha256:e5f6..."),
    appraisal=Appraisal(status="none", verifier="https://verifier.example.org"),
    cnf=ConfirmationKey(jwk=JWK(kty="OKP", crv="Ed25519", x="...")),
)
signed = sign_record(record.model_dump(), load_signing_key())
```

**Verification (offline, 5-step):**

```python
from agentrust_trace import verify_record
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

verify_record(
    signed_record,
    trusted_public_key,        # pinned key from trust store
    max_age_seconds=86400,     # 24h freshness
    revocation=revocation_set, # optional CRL/OCSP
)
```

### Data Format Produced

A single JSON object conforming to `schema/trace-claim.json` (JSON Schema 2020-12). All digests are `sha256:<64 hex>` or `sha384:<96 hex>`. The signature is base64url (no padding). The canonical form for signing uses RFC 8785 (JCS) — not `json.dumps(sort_keys=True)`.

---

## Sample Trace Output

A Level 1 Trust Record (TEE-attested, not yet anchored to transparency log):

```json
{
  "eat_profile": "tag:agentrust-io.com,2026:trace-v0.2",
  "iat": 1782212142,
  "subject": "spiffe://trust.example.org/agent/payments-processor/prod",
  "model": {
    "provider": "anthropic",
    "model_id": "claude-sonnet-4-6",
    "version": "20251001",
    "weights_digest": "sha256:a3f8d2c1e9b04756c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
    "aibom_uri": "https://registry.agentrust-io.com/aibom/claude-sonnet-4-6-20251001"
  },
  "runtime": {
    "platform": "amd-sev-snp",
    "measurement": "sha384:c9e4b1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    "rim_uri": "https://kdsintf.amd.com/vcek/v1/Milan/cert_chain",
    "firmware_version": "1.53.0",
    "nonce": "ZRVkXG1wbVJhY2tSZWNvcmQ"
  },
  "policy": {
    "bundle_hash": "sha256:b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
    "enforcement_mode": "enforce",
    "version": "1.2.0",
    "policy_uri": "https://registry.agentrust-io.com/policy/payments-v1.2.0"
  },
  "data_class": "confidential",
  "tool_transcript": {
    "hash": "sha256:d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    "call_count": 3,
    "transcript_uri": "https://registry.agentrust-io.com/transcript/amd-2026-06-23T09:15:42Z"
  },
  "build_provenance": {
    "slsa_level": 2,
    "builder": "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml",
    "digest": "sha256:e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    "provenance_uri": "https://rekor.sigstore.dev/api/v1/log/entries/def456",
    "provenance_depth": "builder"
  },
  "appraisal": {
    "status": "affirming",
    "verifier": "https://trust-authority.example.org",
    "policy_ref": "https://trust-authority.example.org/policy/sev-snp-agent-v1",
    "timestamp": 1782212145,
    "provenance_depth_verified": "builder"
  },
  "cnf": {
    "jwk": {
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "x9ZBJpokJFQ_oRZzbtzo1Pqqkexd7MqEqP8wsZWdr_c",
      "kid": "sev-snp-workload-key-2026-06-23"
    }
  },
  "signature": "MEUCIQDx_j2lR8k5q2p..."
}
```

---

## Cost Profile

### LLM Token Cost

TRACE makes **zero LLM calls**. It is a governance evidence format and signing protocol. All token costs belong to the agent execution it governs.

### Compute/IO Overhead Per Operation

| Operation | Latency | Notes |
|-----------|---------|-------|
| Record signing (Level 0, Ed25519) | < 1 ms | Software key, single Ed25519 signature |
| Record signing (Level 1, TEE) | 10–50 ms | Attestation quote retrieval + signing |
| Record signing (TPM 2.0) | 50–200 ms | TPM hardware latency |
| Record verification (signature + schema) | < 5 ms | Ed25519 verify + JSON Schema validation |
| RFC 8785 canonicalization | < 1 ms | JCS serialization of ~2 KB record |
| SHA-256 digest of policy bundle | < 1 ms | Typical policy bundles < 100 KB |
| SHA-256 digest of tool transcript | < 1 ms | Proportional to call count |
| SCITT anchoring (Level 2, network) | 100–500 ms | One HTTPS round-trip to transparency log |
| Revocation check (online) | 50–200 ms | CRL/OCSP/SCITT lookup |

### Storage Growth Rate

| Artifact | Size | Retention |
|----------|------|-----------|
| Trust Record (JSON) | 1.5–3 KB per session | Indefinite (audit evidence) |
| Tool transcript (referenced by hash) | Proportional to call count (~500 bytes/call) | Operator-managed |
| SCITT receipt | ~1–2 KB per anchored record | Append-only log, indefinite |

At 1,000 agent sessions/day: ~3 MB/day for Trust Records alone. Minimal compared to observability data.

---

## Validation Criteria

### Quick Smoke Test

```bash
# 1. Install
pip install agentrust-trace

# 2. Generate key and sign a record
python -c "
import time, json
from agentrust_trace import generate_key, sign_record, verify_record

key = generate_key()
record = {
    'eat_profile': 'tag:agentrust-io.com,2026:trace-v0.2',
    'iat': int(time.time()),
    'subject': 'spiffe://test.example.org/agent/smoke-test',
    'model': {'provider': 'anthropic', 'model_id': 'claude-sonnet-4-6'},
    'runtime': {'platform': 'software-only', 'measurement': 'sha256:' + '0'*64},
    'policy': {'bundle_hash': 'sha256:' + 'ab'*32, 'enforcement_mode': 'enforce'},
    'data_class': 'internal',
    'build_provenance': {'slsa_level': 1, 'digest': 'sha256:' + 'cd'*32},
    'appraisal': {'status': 'none', 'verifier': 'https://verifier.example.org'},
}
signed = sign_record(record, key)
verify_record(signed, allow_embedded_key=True)
print('✓ Sign + verify passed')
print(json.dumps(signed, indent=2)[:500])
"

# 3. Run conformance tests
git clone https://github.com/agentrust-io/trace-spec /tmp/trace-spec
cd /tmp/trace-spec && pip install -e . && python -m pytest tests/ -q
```

### Conformance Verification

TRACE defines three conformance levels in [agentrust-io/trace-tests](https://github.com/agentrust-io/trace-tests):

| Level | What is checked |
|-------|----------------|
| 0 | Schema validity, Ed25519 signature, profile URI, freshness |
| 1 | Level 0 + non-zero hardware measurement, affirming appraisal |
| 2 | Level 1 + SCITT receipt resolves on transparency log |

### Key Verification Checks

- `eat_profile == "tag:agentrust-io.com,2026:trace-v0.2"` (v0.1 identifier rejected)
- Signature over JCS canonical form verifies against `cnf.jwk`
- `iat` within 24h of current time (configurable max age)
- `iat` not more than 5 minutes in the future (configurable skew)
- Schema validation against `schema/trace-claim.json` passes
- `origin.kind != "self"` implies `runtime.platform == "software-only"`

---

## Limitations / Out of Scope

| Limitation | Impact | What Implementations Must Add |
|-----------|--------|-------------------------------|
| Does not prevent operator-forged Level 0 records | Software-key records have no hardware root; a privileged operator can forge them | Deploy Level 1+ with TEE-backed keys for third-party verification |
| Does not prove what happened *inside* the model | Internal reasoning, chain-of-thought, context window contents not captured | Combine with model-internal logging if internal state matters |
| Does not prevent replay of valid past records | A valid record from an earlier session can be re-presented | Verifiers must enforce `iat` freshness, require challenge nonces, or check transparency log |
| No runtime telemetry (traces/metrics/logs) | TRACE is evidence, not observability — cannot reconstruct execution timeline | Pair with OpenTelemetry, InsightClaw, or similar for runtime visibility |
| Tool transcript captures only protocol-boundary calls | Functions embedded in the agent binary are not in `tool_transcript` | Only MCP/A2A boundary-crossing calls are recorded; internal functions bind via `build_provenance` |
| TEE side-channel attacks not mitigated | Cache timing, power analysis, speculative execution attacks on TEE | Responsibility of silicon vendor firmware updates |
| Revocation cannot be checked offline | A signed record from a compromised key remains valid without online CRL check | Pass `revocation` store to `verify_record()` for production use |
| No policy evaluation — only policy *binding* | Record proves which policy was in force, not that the policy is correct | Policy review is a separate control |
| SCITT anchor format not yet published | "Verifiable without trusting the operator" is aspirational until the inclusion-proof format ships | Tracked in [#111](https://github.com/agentrust-io/trace-spec/issues/111) |
| MCP and A2A profiles not yet normative | Tool transcript binding exists but normative rules for MCP/A2A are v0.3 targets | Use cMCP for de facto binding today |
| Single-language SDK (Python only for now) | No TypeScript, Go, or Rust verifier yet | Multi-language libraries targeted for v1.0 |
| No encrypted claims envelope | `data_class` and other sensitive fields visible in cleartext | JWE/COSE-Encrypt deferred to v0.3 (open question §7 Q5) |
| `json.dumps(sort_keys=True)` is NOT JCS-conformant | Using Python's default JSON serialization for signing produces non-interoperable records | Must use an RFC 8785 library — diverges on non-ASCII and number formatting |

---

## Evaluation Assessment

### Observability

**Rating: Minimal**

TRACE is not an observability system. It produces governance *evidence*, not runtime telemetry.

**Strengths:**
- The Trust Record itself is a durable, queryable artifact that answers governance questions
- `tool_transcript.call_count` and `tool_transcript.hash` provide summary statistics
- SCITT transparency log enables public audit queries
- `appraisal` field records verifier judgment at a point in time

**Gaps:**
- No traces, metrics, or logs emitted during execution
- No latency, throughput, or error-rate visibility
- No self-monitoring of the signing or verification process
- Cannot reconstruct execution timeline from Trust Records alone (only proves "this happened", not "when each step took")
- No alerting surface — a failed verification is surfaced only to the caller of `verify_record()`

**What implementations must add:** OpenTelemetry or equivalent for runtime visibility. InsightClaw for MCP-level observability. TRACE proves governance compliance; it does not help debug performance.

---

### Security

**Rating: Strong**

Security is TRACE's core design objective. The specification is built around hardware-rooted cryptographic evidence.

**Strengths:**
- Hardware root of trust (AMD SEV-SNP, Intel TDX, NVIDIA H100): signing key never leaves TEE
- Silicon root → platform attestation key → workload key → record-signing key hierarchy
- Ed25519/ES256/ES384 signatures over RFC 8785 canonical JSON (deterministic, interoperable)
- Mandatory signature binding — unsigned records are rejected by spec and by `verify_record()`
- `cnf.jwk` must not contain private key material (model validator rejects `d`, `p`, `q`, etc.)
- Freshness binding: `iat` + max-age + max-future-skew + optional challenge nonce
- Revocation checking: fail-closed semantics (unavailable CRL = rejection)
- Cross-field integrity: `origin.kind != "self"` cannot claim hardware `runtime.platform`
- Policy hash sealed to TEE measurement — substituting policy invalidates the runtime claim
- Closed-set enums (`enforcement_mode`, `origin.kind`, `platform`) limit semantic ambiguity
- Build provenance depth verification with fail-on-contradiction semantics
- Explicit threat model (§2): named adversaries, named assumptions, named TCB boundaries
- Level 0/1/2 progressive trust levels with clear guarantees at each

**Gaps:**
- Level 0 (software-only) records provide no hardware protection — suitable only for dev/staging
- No encrypted-claims transport yet (sensitive `data_class` visible in cleartext records)
- Revocation check is optional (caller must pass `revocation` store; default is offline-only)
- No key rotation protocol in the spec (implementations decide rotation at TEE-image boundaries)
- Action receipt verification depends on external issuer PKI not specified by TRACE
- TEE side-channel attacks explicitly out of scope

---

### Identity Management

**Rating: Strong**

TRACE binds workload identity, model identity, and key identity into a single verifiable artifact.

**Strengths:**
- `subject` requires SPIFFE SVID or DID URI — both are cryptographically verifiable identity schemes
- SPIFFE identity bound to TEE measurement (identity rooted in hardware, not operator config)
- `model` field identifies provider, model ID, version, and optionally weights digest + AIBOM URI
- `cnf.jwk` is a proof-of-possession key that binds the record to a specific TEE-held private key
- RFC 7638 JWK Thumbprint provides stable key identifier across representations
- `delegation` block creates an offline-verifiable delegation DAG for multi-agent A2A chains
- `origin` block distinguishes self-produced vs third-party-assembled records (disambiguation of "who said this")
- Agent handoff chain captured across protocol boundaries via `parent_record_hash`

**Gaps:**
- No human user identity binding — TRACE identifies the *workload*, not the human who triggered it
- No OAuth/OIDC integration — human principal must be bound at the orchestration layer
- Key-to-organization binding is out-of-band (nothing in the record ties `cnf.jwk` to a legal entity)
- `model_id` is a string asserted by the producer — no verification that the named model actually ran (except at Level 1+ where the measurement covers the binary)
- Cross-organizational identity federation not specified (each org manages its own SPIFFE trust domain)

---

### Reliability

**Rating: Moderate**

TRACE is a record format and signing protocol, not a distributed system. Reliability concerns apply to the verification and anchoring flows.

**Strengths:**
- Offline verification: no callback to issuer, no network dependency for signature + schema check
- Records are self-contained and portable — survive infrastructure failures, cloud migrations
- Schema validation rejects malformed records before cryptographic work
- Profile check runs before signature verification (fail-fast on wrong semantics)
- Deterministic canonicalization (RFC 8785) ensures cross-implementation reproducibility
- Graceful degradation: Level 2 → Level 1 when transparency log is unavailable (freshness nonce still works)
- Test suite enforces conformance across implementations

**Gaps:**
- No delivery guarantee — the SDK produces records but does not ensure they reach a verifier or log
- No retry logic for SCITT anchoring (transparency log submission is fire-and-forget in the SDK)
- No ordering guarantee across records — multiple Trust Records for the same session have no defined sequence (except via `delegation` chains)
- Record deduplication not specified — same session could produce multiple valid records
- No backpressure mechanism — a high-throughput agent emitting per-call records has no rate limiting
- Key loss is catastrophic: no recovery mechanism if the TEE-bound key is destroyed
- Verifier availability for `appraisal` field is not specified (what happens when the verifier is down?)

**What implementations must add:** Reliable transport (queue or persistent store) for records in transit to verifiers/logs. Retry with backoff for SCITT submission. Deduplication at the consumer.

---

### Accuracy

**Rating: Strong**

TRACE makes strong correctness guarantees through cryptographic binding and deterministic canonicalization.

**Strengths:**
- Cryptographic binding: every field is covered by the signature — modification of any field invalidates the record
- RFC 8785 (JCS) canonicalization with explicit UTF-16 code-unit sort order (not Python `sorted()`)
- SHA-256/SHA-384 digests for all hashed fields with regex-enforced format
- Pydantic model validation rejects structurally invalid records at construction time
- JSON Schema validation enforces field types, enums, and cross-field constraints
- `provenance_depth` and `provenance_depth_verified` distinguish issuer claims from verifier reality
- Explicit handling of contradictions: evidence that resolves and contradicts fails the appraisal (no silent downgrade)
- `enforcement_mode: "declared"` is honest about the absence of evaluation (no false claims of enforcement)
- Content-marking spec (v1) binds C2PA assertions to Trust Records by hash, detecting substitution
- Canonicalization boundary test vectors ensure cross-implementation agreement on edge cases (non-BMP characters, surrogate pairs)

**Gaps:**
- `tool_transcript.hash` commits to what was recorded at the protocol boundary, not what actually happened (if the gateway has a bug, the hash is accurate but the transcript is wrong)
- `data_class` is asserted by the policy engine, not verified by the record format — a misconfigured classifier produces an accurate record of an inaccurate classification
- Build provenance at `surface` depth only checks digest and builder membership — no verification that the artifact at that digest actually contains the claimed code
- `call_count` is metadata, not cryptographically bound independently of the transcript hash
- Cross-boundary data propagation uses temporal adjacency as a proxy (cannot prove causation between tool calls)
- Timestamp accuracy depends on the TEE's notion of time — no NTP verification

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Minimal | Not an observability system; no traces/metrics/logs emitted |
| Security | Strong | Level 0 provides no hardware protection; no encrypted-claims transport yet |
| Identity | Strong | No human user binding; model identity is asserted, not verified below Level 1 |
| Reliability | Moderate | No delivery/retry/dedup guarantees; SDK is produce-only |
| Accuracy | Strong | Transcript accuracy bounded by gateway correctness; data_class is asserted not verified |
