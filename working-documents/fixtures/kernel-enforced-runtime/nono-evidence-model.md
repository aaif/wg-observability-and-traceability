# nono evidence model: canonical field reference for AAIF working-group mappings

**This is the single source of truth for every nono field cited in the AAIF working-group documents under this folder.** WG-facing documents map these fields to a group's own vocabulary; they do not redefine them. Cite this file at a commit SHA.

Source: v0.77.0 (2026-09-11); checked against `main` at 7450e43. Files: `crates/nono/src/audit.rs`, `crates/nono/src/undo/types.rs`, `crates/nono/src/supervisor/types.rs`, `crates/nono-proxy/src/audit.rs`, `docs/protocols/audit-delivery-v1.md`, `docs/protocols/approval-webhook-v1.md`.

Schema stability: no scheme label is stamped on records yet; nono #1918 is defining a version and metadata contract across audit events and attestation bundles. Until it lands, treat field names as stable at the cited SHA and re-check on each release.

## 1. Terminology, mapped to the AAIF vocabularies

| nono term | T&O plane | I&T Actor and Control Model |
|---|---|---|
| Session (`nono run` from start to exit) | Execution | Agent Instance lifecycle |
| Supervisor (trusted parent process outside the sandbox) | Execution | Controller-side recorder; not reachable by the Agent Instance |
| Capability decision (filesystem, network, or command request judged by policy or an approval backend) | Execution, Protocol | Authorization event; Relying Party decision |
| Network event (proxy-observed request, allow or deny, credential handling) | Protocol | Resource Server access with credential provenance |
| Command policy decision (mediated command under a tool-sandbox profile) | Execution | Bounded authority at the tool level |
| Phantom token (agent holds a placeholder; proxy substitutes the real credential per request) | Protocol | Credential the Agent Instance never possesses |
| SPIFFE delegation context (`act` claim chain from a JWT-SVID) | Context | Human Principal to Agent Instance to Sub-agent lineage |
| Audit event record (one NDJSON line with chain hash) | All | Audit primitive |

## 2. The evidence model as shipped

### 2.1 Event types

Every session writes `audit-events.ndjson`. The payload enum (`AuditEventPayload`, tagged by `type`) has seven variants:

- `session_started`: ISO-8601 start, redacted command line, optional redaction-policy delta from the secure default.
- `session_ended`: end timestamp, child exit code.
- `capability_decision`: an `AuditEntry` containing the request (capability, network, or command), the decision (`Granted`, `Denied { reason }`, `Timeout`), the approval backend that handled it, and decision latency in milliseconds.
- `network`: a `NetworkAuditEvent` (section 3.3).
- `command_policy`: a `CommandPolicyAuditEvent` with caller identity (label, kind, pid, session root pid), decision and reason, hashes of argv, environment names, and cwd, redacted display forms, exit code, and stdio byte accounting.
- `sandbox_runtime`: platform, Landlock ABI version, whether execute restrictions were enforced, whether tool-sandbox mediation was active.
- `url_open`: supervisor-mediated browser launches (OAuth flows), success or error.

### 2.2 Record envelope and integrity

Each line is an `AuditEventRecord`:

```
sequence      monotonic, from 0
prev_chain    previous record's chain hash, null for the first record
leaf_hash     SHA-256 over domain-separated canonical event JSON
chain_hash    SHA-256 over domain separator || prev_chain || leaf_hash
event         the payload above
```

At session end the supervisor emits an `AuditIntegritySummary`: hash algorithm, event count, chain head, and a Merkle root over the ordered leaves. Inclusion proofs (`AuditInclusionProof`) can be generated for any single event against that root. Optionally the session is wrapped as an in-toto statement with predicate type `https://nono.sh/attestation/audit-session/alpha` in a signed bundle, and the audit delivery protocol v1 ships the complete log plus a canonical session digest to a control plane that recomputes the chain and root independently.

The property that matters for E3: the agent process cannot write to this log. It is produced by the supervisor, which the sandboxed child cannot reach. Tampering after the fact breaks the chain; omission is detectable by sequence gap.

### 2.3 Network events

`NetworkAuditEvent` carries, per request:

- `mode`: `connect` (host filtering only, no L7 visibility), `connect_intercept` (tunnel terminated locally for L7 inspection or credential injection), `reverse`, `external`.
- `decision`: `allow`, `deny`, `approve_requested`, `approve_granted`, `approve_denied`, `approve_timeout`, `approve_error`.
- `denial_category` when denied: `authentication_failed`, `endpoint_policy`, `managed_credential_unavailable`, `host_denied`, `intercept_handshake_failed`, `upstream_connect_failed`, `connect_bypasses_l7`, `external_proxy_rejected`, `unsupported_upgrade`.
- `auth_mechanism`: `proxy_authorization`, `phantom_header`, `phantom_path`, `phantom_query`, `spiffe_jwt_bearer`, `spiffe_oauth_assertion`; and `auth_outcome`.
- `managed_credential_active`, `injection_mode` (`header`, `url_path`, `query_param`, `basic_auth`, `oauth2`, `spiffe_jwt`).
- `endpoint_policy_action`, `endpoint_policy_rule`, `approval_backend`.
- `route_id`, `target`, `upstream` (credentials stripped), `port`, `method`, `path`, `status`, `reason`.
- Credential capture accounting (action, name, redacted command, exit status, duration, byte counts). Credential values are never stored.
- `spiffe_context`: workload SPIFFE ID, trust domain, SVID type, source, optional upstream SPIFFE ID, and a `delegation` block with `authorized_by` (`act.sub`), `on_behalf_of` (root `sub`), and `chain_depth`.


## 3. Evidence grade

Using the AAIF Observability & Traceability use-case E4 ladder (E0 Declared, E1 Observed, E2 Enforced, E3 Corroborated, E4 Anchored): the log is E2 by construction, because the supervisor records what it and the kernel enforced rather than what the agent reports; E3 when the signed in-toto bundle exists; E4 depends on external timestamping and independent recomputation at ingest via audit-delivery-v1.

## 4. What the record does not contain

- Kernel decisions. A Landlock or Seatbelt denial is an errno in the child, observable by pid through kernel tracing, not through this log. `sandbox_runtime` records the boundary once; it does not record per-syscall outcomes.
- W3C trace context. No record carries `trace_id` or `span_id`, and the three W3C environment variables are not forwarded into the sandbox by default. Tracked in the nono issue linked from `02-observability-traceability/`.
- Correlation IDs (`invocation_id`, `interaction_id`): additive fields in review, nono #1693 / PR #1704.
- Human identity for approvals: the approval backend's own response may carry it (approval-webhook-v1); the runtime record carries the backend name, decision, reason, and latency only.
- AAuth identity: on the unmerged `AAuth` branch only; see `03-identity-trust/`.
