# AAIF Reference Architecture: nono

| Field | Value |
|-------|-------|
| **Subject** | [nono](https://github.com/nolabs-ai/nono) |
| **Version** | 0.77.0 (2026-09-11); claims checked against `main` at 7450e43 |
| **Date** | 2026-09-16 |
| **Author** | Sal Kimmich (Nolabs). Drafted with AI assistance; every field name below was checked against source. |

---

## Objective

Reference architecture for nono, a Rust supervisor that launches an agent process inside a kernel-enforced sandbox, brokers filesystem, network, command, and credential capability per invocation, and writes a hash-chained audit log the agent cannot reach; assessed as an enforcement-point evidence source for agent observability.

---

## Scope / Zoom Level

**Primitive layer, at the Agent → Tool and Agent → Runtime boundaries of the cross-boundary model.** nono sits between the agent process and the operating system. It does not instrument the model call, the agent framework, or the tool's own internals. Everything it records is a decision made at a boundary the agent process cannot cross without it: a file open, a socket connect, a mediated command launch, a credential use.

It is not a kernel tracer. A Landlock or Seatbelt denial is visible to LTTng, ftrace, or the platform audit subsystem as a failed syscall by pid; nono records the policy decision that caused it, from the supervisor. The two are complementary layers of the same event, and the landscape's `02-kernel-tracing` tools are the right place to look for the syscall-level view.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| nono | 0.77.0 | `crates/nono` (library), `nono-cli`, `nono-proxy` |
| Linux kernel | 5.13+ for filesystem Landlock; 6.7+ (ABI 4) for TCP network filtering; ABI 6 for signal and abstract-socket scoping | nono detects the ABI at start and records it |
| macOS | Seatbelt | filesystem and process restrictions; no per-invocation network Landlock equivalent |
| SPIFFE Workload API | optional | for JWT-SVID routes and RFC 8693 delegation context |
| Approval backend | optional | `terminal`, `webhook` (approval-webhook-v1), or `chain` |
| Control plane | optional | audit-delivery-v1 for signed ingest and independent recomputation |
| OpenTelemetry | not integrated | see Limitations; this is the gap this document is filed to close |

---

## Architecture Diagram

```
                       host (unsandboxed)
 ┌────────────────────────────────────────────────────────────────┐
 │  nono supervisor (Capability Broker)                            │
 │   ├─ policy engine: profile → Landlock/Seatbelt ruleset         │
 │   ├─ approval backends: terminal | webhook | chain              │
 │   ├─ credential store: keyring / file / env / 1Password         │
 │   ├─ AuditRecorder ──► audit-events.ndjson  (hash chain)        │
 │   │                    audit-attestation.bundle (in-toto, opt)  │
 │   └─ nono-proxy (L7) ──► upstream APIs                          │
 │        phantom token in, real credential out, per request       │
 └───────────┬────────────────────────────────────▲────────────────┘
             │ spawn with ruleset applied         │ Unix socket IPC
             │ (irreversible, inherited)          │ capability requests,
             ▼                                    │ URL-open requests
 ┌────────────────────────────────────────────────┴───────────────┐
 │  sandboxed agent process (claude, codex, goose, custom)         │
 │   • sees only granted paths and the proxy port                  │
 │   • holds phantom tokens, never upstream credentials            │
 │   • cannot open or write audit-events.ndjson                    │
 │                                                                  │
 │   Tool Sandbox: `git` ──shim──► fresh child sandbox for `git`   │
 │                   (only git's declared grants and credentials)  │
 └──────────────────────────────────────────────────────────────────┘

 telemetry emission points (all from the supervisor, none from the agent):
   [A] capability_decision   supervisor, per request over IPC
   [B] command_policy        supervisor, per mediated command
   [C] network               proxy, per request (buffered to session end)
   [D] sandbox_runtime       supervisor, once at start
   [E] session_started/ended supervisor
```

Where the kernel sits relative to the record:

```
   agent syscall ──► kernel LSM (Landlock/Seatbelt) ──► allow / EPERM
                             │                            │
                             │ no event to nono           │ visible to ftrace / LTTng / auditd
                             ▼
   agent asks supervisor ──► [A] capability_decision ──► ruleset change or denial
   agent execs `git`    ──► [B] command_policy       ──► child sandbox + exit code
   agent sends HTTP     ──► [C] network              ──► proxy decision + credential handling
```

---

## Instrumentation Walkthrough

**What is captured.** Every `nono run` session writes `audit-events.ndjson`, one JSON record per line. Seven payload types, tagged by `type`:

| Type | Emitted when | Key fields |
|---|---|---|
| `session_started` | launch | ISO-8601 start, redacted argv, redaction-policy delta |
| `sandbox_runtime` | after ruleset applied | platform, Landlock ABI, execute enforcement flag, tool-sandbox active flag |
| `capability_decision` | agent (via SDK) requests a path, host, endpoint, or command not in policy | request (`capability` / `network` / `endpoint` / `command` with request_id, child_pid, session_id, reason), decision (`Granted` / `Denied{reason}` / `Timeout`), backend, duration_ms |
| `command_policy` | a mediated command runs | command, caller, caller_pid, shim_pid, session_root_pid, decision, reason (policy edge), argv/env-name/cwd hashes, redacted displays, exit_code, stdio byte accounting |
| `network` | proxy handles a request | mode (`connect` / `connect_intercept` / `reverse` / `external`), decision, route_id, auth_mechanism, auth_outcome, managed_credential_active, injection_mode, denial_category, endpoint_policy_action/rule, approval_backend, spiffe_context (workload id, trust domain, delegation `authorized_by` / `on_behalf_of` / `chain_depth`), target, upstream, method, path, status |
| `url_open` | agent asks supervisor to open a browser URL (OAuth) | request_id, url, child_pid, session_id, success, error |
| `session_ended` | exit | end timestamp, exit_code |

**The mechanism.** The supervisor is the only writer. The agent reaches it over a Unix socket for capability and URL-open requests; the proxy reaches it in-process. The child's ruleset is applied before exec and inherited by every descendant, so a tool the agent spawns is inside the same boundary or, under Tool Sandbox, inside a narrower one built only from that command's policy.

**Integrity.** Each record is `{sequence, prev_chain, leaf_hash, chain_hash, event_json, event}`. `leaf_hash = SHA-256("nono.audit.event.alpha\n" || canonical event bytes)`; `chain_hash = SHA-256("nono.audit.chain.alpha\n" || prev_chain_or_zero || leaf_hash)`. At exit the supervisor emits an integrity summary (chain head, Merkle root over ordered leaves) and can produce an inclusion proof for any single record. Optionally the session is wrapped as an in-toto statement (predicate `https://nono.sh/attestation/audit-session/alpha`) in a signed bundle, and audit-delivery-v1 ships log plus canonical session digest to a control plane that recomputes everything independently.

In the use-case inventory's evidence-grade ladder (E4): the log is **E2 Enforced** by construction, **E3 Corroborated** when the signed bundle exists, and depends on external timestamping and independent recomputation at ingest for **E4 Anchored**.

**Identity carried on network events.**

- SPIFFE: when a JWT-SVID route is active, `spiffe_context` records the workload SPIFFE ID, trust domain, SVID type, and the RFC 8693 `act` chain as `authorized_by` (act.sub), `on_behalf_of` (root sub), `chain_depth`. These are shipped values for two attributes proposed in issue #50.
- AAuth (unmerged branch `AAuth`, Aleksy Siek, 2026-08-13, 282 files behind current `main`): adds RFC 9421 HTTP Message Signatures with an Ed25519 agent key, `hwk` and `jwks_uri` schemes, a new `aauth_signature` auth mechanism and injection mode, and an `aauth_context` on each network event carrying `agent_id`, `scheme`, `issuer`, `key_thumbprint`. This is the implementation side of the aauth.dev claims issue #50 cites. Status: not in any release; do not cite as shipped.

---

## Sample Trace Output

A seven-record session (coding agent asked to open a pull request). Field order is the v0.77.0 serde output; hashes are computed with the alpha scheme and the generator reproduces the repository's golden vector first. `event_json` omitted for readability; the file carries it and verifiers hash it.

```json
{"sequence":0,"prev_chain":null,
 "leaf_hash":"51a8385a308cb2f32ea6d6578ba20d72b8b16aa0be8fefe54a65d1beaa3502c0",
 "chain_hash":"22675fa1209f86383304a8e041c51cd7fbb8f9840c6fafa094ba29e30e64cca6",
 "event":{"type":"session_started","started":"2026-09-16T16:40:00.000Z",
          "command":["claude","--print","open a PR for the changelog fix"]}}

{"sequence":1, ... "event":{"type":"sandbox_runtime","event":{"timestamp":"2026-09-16T16:40:00.041Z",
 "platform":"linux","landlock_abi":"6","landlock_execute_enforced":true,"tool_sandbox_active":true}}}

{"sequence":2, ... "event":{"type":"capability_decision","entry":{
 "timestamp":{"secs_since_epoch":1789663261,"nanos_since_epoch":118000000},
 "request":{"capability_type":"capability","request_id":"01K5ATQ2W8H0R7M3F1Z9C4X6DE",
            "path":"/home/sal/.ssh/id_ed25519","access":"Read","reason":"read deploy key for git push",
            "child_pid":48213,"session_id":"019a2c1e-5f60-7c3a-9b1d-4e2f8a7c6d10"},
 "decision":{"Denied":{"reason":"denied by operator"}},"backend":"terminal","duration_ms":6420}}}

{"sequence":3, ... "event":{"type":"command_policy","event":{"timestamp":"2026-09-16T16:41:07.512Z",
 "command":"git","caller":"session","caller_pid":48213,"shim_pid":48377,"session_root_pid":48201,
 "decision":"allow","reason":"command_policies.commands.git.from.session","stdio_mode":"inherit",
 "argv_display":["git","push","origin","fix/changelog-links"],"exit_code":0, ...}}}

{"sequence":4, ... "event":{"type":"capability_decision","entry":{
 "request":{"capability_type":"endpoint","route_id":"github","upstream":"https://api.github.com",
            "method":"POST","path":"/repos/nolabs-ai/nono/pulls","rule_label":"github.write", ...},
 "decision":"Granted","backend":"webhook","duration_ms":4218}}}

{"sequence":5, ... "event":{"type":"network","event":{"timestamp_unix_ms":1789663276551,
 "mode":"reverse","decision":"approve_granted","route_id":"github",
 "auth_mechanism":"spiffe_jwt_bearer","auth_outcome":"succeeded","managed_credential_active":true,
 "injection_mode":"spiffe_jwt","endpoint_policy_action":"approve","endpoint_policy_rule":"github.write",
 "approval_backend":"webhook",
 "spiffe_context":{"workload_spiffe_id":"spiffe://nolabs.example/agent/claude-code/laptop-sal",
   "trust_domain":"nolabs.example","svid_type":"jwt","source":"workload_api",
   "delegation":{"authorized_by":"spiffe://nolabs.example/session/019a2c1e",
                 "on_behalf_of":"spiffe://nolabs.example/user/sal","chain_depth":1}},
 "target":"api.github.com","method":"POST","path":"/repos/nolabs-ai/nono/pulls","status":201}}}

{"sequence":6, ... "event":{"type":"session_ended","ended":"2026-09-16T16:41:20.904Z","exit_code":0}}
```

Integrity summary at exit:

```json
{"hash_algorithm":"sha256","event_count":7,
 "chain_head":"5dfe70aaa914029c4bdda90a0fd97dc79a75578db710a41f13d0dcf9b4425f62",
 "merkle_root":"0377ef310ef8b7e1a5af1f2f5192090d10478734aa52159f94e928b488ebcd85"}
```

Full fixture and generator: `fixtures/kernel-enforced-runtime/audit-events.ndjson`, `gen_session.py`.

---

## Cost Profile

| Cost | Value |
|---|---|
| LLM token cost | none; nono never calls a model |
| Startup | no container image or daemon; ruleset applied at exec (project docs contrast with 100-500 ms per Docker invocation; no independent benchmark published) |
| Per mediated command | one extra process (shim) and one child sandbox construction; not benchmarked publicly |
| Per proxied request | one L7 hop on localhost; credential injection is header rewriting |
| Storage growth | one NDJSON line per event; a `network` record is roughly 0.5 to 1.5 KB with SPIFFE context; proxy buffer capped at 4096 events per session in memory until PR #831 lands |
| Approval latency | recorded per decision in `duration_ms`; operator or webhook time dominates |

---

## Validation Criteria

1. `nono run --allow-cwd -- your-agent`, then `nono audit show --json` on the session: seven-plus records, sequences contiguous from 0.
2. Recompute: hash `event_json` of any record with the alpha domain separator and confirm it equals `leaf_hash`; chain forward and confirm the final `chain_hash` equals the integrity summary's `chain_head`.
3. Tamper test: edit one byte of any `event_json` and rerun verification; every later `chain_hash` and the Merkle root must mismatch.
4. Boundary test: from inside the session, attempt to append to `audit-events.ndjson`; expect EPERM.
5. Credential test: with a phantom or SPIFFE route active, dump the agent process environment and memory-visible headers; the upstream credential must not appear, and the `network` record must show `managed_credential_active: true`.

---

## Limitations / Out of Scope

| Limitation | Detail | Tracking |
|---|---|---|
| **No W3C trace-context propagation into the sandbox** | nono does not read, forward, or emit `TRACEPARENT`, `TRACESTATE`, or `BAGGAGE`. Tool Sandbox filters child environments through `environment.allow_vars`, so unless a profile allow-lists those names, the OpenTelemetry environment carrier is stripped at exactly the boundary the WG's local-CLI deep-dive identifies as critical. No audit record carries a `trace_id`. | nono issue to be filed by this author: default allow-list for the three W3C variables plus `trace_id` / `span_id` on every audit record |
| No OTLP export | `audit-events.ndjson` is the only surface; a downstream consumer already reads it directly (nono #1925) | unclaimed; reference-implementation slot for this WG |
| No correlation IDs | events carry pids, hashes, timestamps; `invocation_id` / `interaction_id` are additive fields in review | nono #1693, PR #1704 |
| Network events buffered to session end | 4096-event in-memory cap; crash loses them | nono #798, PR #831 |
| Per-invocation scope is per mediated command, not per MCP tool call | an MCP tool call inside the agent process that does not exec a mediated command runs under the session grant | design; SAF-M-74 describes the target |
| Approval-gated runtime filesystem grants for commands | not shipped | nono #1621 |
| L7 visibility only in `connect_intercept` and `reverse` modes | plain `connect` is host-filtered without inspection; `connect_bypasses_l7` denial category exists to refuse it | design |
| Kernel decisions are not events | a Landlock/Seatbelt denial is an errno in the child; observable via kernel tracing by pid, not via nono | see Scope |
| Selective disclosure | beta scheme with per-leaf nonce in review | nono PR #1651 |
| Schema versioning | no scheme label in records yet | nono #1918 |
| macOS network filtering | no per-invocation network Landlock equivalent under Seatbelt; proxy still applies | platform |
| Independent audit | none published; OSTIF / X41 D-Sec engagement scoped | pending |

---

## Evaluation Assessment

**Observability: Partial.** The supervisor produces complete, structured, per-decision records for everything that crosses the broker or proxy, and nothing for the model call or the tool's internals. It does not observe itself beyond `sandbox_runtime`. No metrics, no OTLP, no trace-context propagation. Implementations would need to add the environment-carrier allow-list, `trace_id` on records, and an exporter.

**Security: Strong.** Kernel-enforced, irreversible, inherited ruleset; credentials never in the agent process on phantom or SPIFFE routes; append-only log written by a process the agent cannot reach; hash chain plus Merkle root plus optional signed attestation. Gaps: no published third-party audit; network-event buffering weakens crash-time evidence until #831.

**Identity Management: Moderate.** SPIFFE workload identity and RFC 8693 delegation chain are recorded per request when configured; approval backend and operator decisions are recorded with latency. Human principal is present only through SPIFFE `on_behalf_of` or the approval record; there is no session-level principal binding otherwise. AAuth agent identity exists on a branch only.

**Reliability: Partial.** Supervisor events flush per record; proxy events do not (buffered, capped, dropped on overflow with a warning). Ordering is by `sequence`. No deduplication or backpressure semantics because there is no delivery pipeline beyond audit-delivery-v1's durable retry outbox.

**Accuracy: Strong for what it records.** Values are taken from the enforcement path, not reported by the agent (E2 on the evidence ladder). Redaction of argv, headers, and URLs is pattern-based and best-effort; hashed fields are the evidentiary values, displayed fields are not.

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Partial | no trace-context propagation, no OTLP, no `trace_id` on records |
| Security | Strong | no published independent audit; buffered network events |
| Identity | Moderate | principal binding only via SPIFFE or approval records; AAuth unmerged |
| Reliability | Partial | proxy events buffered and capped until PR #831 |
| Accuracy | Strong | best-effort redaction on display fields |
