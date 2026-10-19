# Cross-Boundary Model: Runtime and HITL Rows for a Kernel-Enforced Local Realization

**Status:** First filled pass for two `?` rows, ready for WG review

**Last updated:** 2026-09-16

**Owner:** Sal Kimmich, following the invitation in issue #29 and the Sept 2 decision to place below-L7 work in the Primitives and Protocol Observability focus group

**Inputs:** cross-boundary observability model (PR #25), the merged local-CLI deep-dive, OpenTelemetry GenAI and CLI conventions, W3C Trace Context and Baggage, SAF-MCP mitigation SAF-M-74 (per-invocation capability brokering) and its three listed implementations: nono (Nolabs), Kubefence (Red Hat NRI plugin), AgentBound (academic). Field-level evidence for the nono realization is in `tracing_landscape/05-ai-agent-observability/AAIF-REF-ARCH-NONO.md`.

## 1. Purpose

Section 5 of the model leaves three rows unfilled: Agent → MCP Server (now covered by PR #32), Agent → Gateway or Runtime, and Agent → Human (HITL). This document fills the last two from the viewpoint of a **runtime that enforces policy at the OS boundary and brokers capability per invocation**. Any runtime of that class can satisfy the rows; the cited fields are what one shipped implementation records today, so the rows are grounded rather than aspirational.

It also adds observed values to the Security and Provenance cells of the existing Agent → Tool row, where the merged local-CLI deep-dive records the gap as "no common record of declared versus observed permissions or granted versus used scope."

Vendor neutrality: nothing here requires a particular runtime. Where a field exists only in one implementation it is marked as such.

## 2. Boundary description

```
optional upstream caller
  └── agent turn / invocation
      └── [Agent → Runtime]   runtime admits the agent process under a declared boundary
          ├── tool execution span                          ← Agent → Tool
          │     └── [Runtime → Local Process]  child launched under a narrower boundary
          ├── capability request ──► decision              ← Agent → Runtime (broker)
          │     └── [Agent → Human (HITL)]  approval backend consulted, human answers
          └── egress request ──► proxy decision            ← Agent → Runtime (proxy, L7)
                └── credential injected outside the agent's reach

 kernel enforcement (Landlock / Seatbelt / NRI hooks) sits under every arrow.
 It produces no runtime events. It is observable by pid via kernel tracing,
 and it is the reason the runtime's record of what crossed is complete.
```

The runtime boundary has three surfaces:

1. **Admission surface.** The runtime declares the boundary once, before exec: platform, enforcement mechanism and version, whether execute restrictions are enforced, whether per-command mediation is active.
2. **Broker surface.** The agent asks for something outside its grant (a path, a host, an L7 endpoint, a command). The runtime decides locally by policy or consults an approval backend. The decision, the backend, and the latency are recorded.
3. **Egress surface.** The agent's HTTP leaves through a local L7 proxy that decides per request and substitutes real credentials for placeholders. Auth mechanism, credential handling, delegation context, and upstream result are recorded.

## 3. Filled rows

| Boundary | Identity | Context | Relationship | Lifecycle | Outcome | Provenance | Security | Timing |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Agent → Gateway or Runtime (kernel-enforced local realization) | Session ID; agent root PID; runtime platform and enforcement ABI; per-request `request_id` and requesting child PID; workload identity (SPIFFE ID, trust domain) when configured; route ID for egress | Declared profile (grants, mediated commands, credential references by name); redaction policy delta; for egress, route, method, path, upstream host without credentials; for commands, hashed argv, env names, cwd plus redacted displays | Runtime is the observer-of-record for the agent and every descendant; capability requests link to the child PID that raised them; mediated commands link caller PID, shim PID, and session root PID; egress links to route and, when present, to the approval that unlocked it | admitted (`sandbox_runtime`) → running → per-request: requested → decided (granted / denied / timeout / approve_* states) → executed / forwarded → exited (`session_ended`, exit code) | Per decision: granted, denied with reason, timeout; per command: exit code and stdio byte accounting; per egress: upstream status and denial category; per session: exit code and integrity summary | Enforcement mechanism and version recorded at admission; policy edge that allowed each command (`reason` names the profile rule); approval backend that decided; evidence class: enforcement-side (E2 on the E4 ladder), E3 with signed attestation | What was requested vs what was granted, per decision; credential mechanism and whether the agent ever held the credential (`managed_credential_active`, phantom / SPIFFE injection modes); delegation chain (`authorized_by`, `on_behalf_of`, `chain_depth`); append-only hash-chained record the agent cannot write | Admission timestamp; per-decision `duration_ms`; per-egress `timestamp_unix_ms`; session start and end. Gap: no trace-context timestamps because the carrier is not propagated (see section 5) |
| Agent → Human (HITL) via approval backend | `request_id`; requesting child PID; session ID; backend name (`terminal`, `webhook`, `chain`); human identity only if the backend records it (webhook v1 carries it in its own response, not in the runtime record) | The proposed action as the runtime saw it: path and access mode, host and port, L7 route/method/path and matched rule label, or command and args; the agent's stated `reason` | Approval refers to exactly one proposed action by `request_id`; a denial produces no execution record for that action; an approval is followed by the runtime's own execution or egress record for the same request | requested → backend consulted → granted / denied / timeout / error → (if granted) executed | Decision and reason; timeout is a distinct outcome, not a denial | Which backend answered; for webhook, the endpoint is named in the profile, not the record; evidence class: enforcement-side, because the runtime records the decision it then enforced rather than a decision the agent reports | Approval is bound to a runtime-enforced action, so "observed approval is not proof of enforcement" (issue #44) is answered: the runtime's record is the enforcement. Human identity and step-up assurance level are not carried in the runtime record today | Decision latency in `duration_ms`; no separate timestamps for "surfaced to human" vs "human answered" |

### 3.1 Additions to the Agent → Tool row (Security and Provenance cells)

| Cell | Observed values in a kernel-enforced realization |
| :-- | :-- |
| Security | Declared permissions: the profile grant for the session and the per-command policy for a mediated tool. Observed: the `command_policy` decision and the `reason` naming the policy edge; the `capability_decision` for anything requested beyond the grant; for egress, the proxy decision, denial category, and credential mechanism. Granted vs used: a granted capability with no subsequent execution or egress record is granted-but-unused; a denied request is a scope-exceed attempt that never executed. Sandbox and egress policy are recorded once at admission and referenced by rule label per decision. |
| Provenance | Executable resolution is by policy: a mediated command runs the pinned or `PATH`-resolved executable under the runtime's control, and the launch is recorded with hashed argv and cwd. Declared tool schema vs resolved command divergence is visible because the runtime records what was exec'd, not what the agent said it would exec. Instrumentation producer is the runtime, evidence class enforcement-side. |

## 4. Standards coverage

| Need | Standard | Coverage in this realization |
| :-- | :-- | :-- |
| Tool identity and call ID | OTel GenAI `execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id` | Not present; the runtime does not see the framework's tool-call ID. Correlation must come from trace context or the additive `invocation_id` (nono #1704) |
| Process identity and exit | OTel CLI conventions (`process.executable.*`, `process.pid`, `process.exit.code`) | Present as command, caller PID, shim PID, session root PID, exit code |
| Causality | W3C Trace Context, OTel environment-variable carrier | **Not propagated.** See section 5 |
| Approval evidence | none in OTel today; issue #44 defines the relationship | Present as `capability_decision` with backend and latency |
| Delegation | RFC 8693 `act` chain; issue #50 proposes `agent.delegation_depth` | Present as `authorized_by`, `on_behalf_of`, `chain_depth` on SPIFFE routes |
| Tamper evidence | use case E4; Sigstore / in-toto for signing | Present: hash chain, Merkle root, inclusion proofs, optional in-toto bundle |

## 5. The propagation gap, stated as a finding against the reference implementation

The merged local-CLI deep-dive says context must cross during process creation and warns that runtimes filter or reconstruct child environments. In the nono realization that warning is true today: the runtime does not read, forward, or emit `TRACEPARENT`, `TRACESTATE`, or `BAGGAGE`, its per-command environment filter allow-lists by name, and no audit record carries a `trace_id`. A span emitted by a tool inside the sandbox cannot parent to the agent's tool span unless the profile author happened to allow-list those variables.

Proposed fix, to be filed against nono by this author and cited here once it has a number: allow-list the three W3C variables by default in every child environment (they carry no secrets by specification), and add `trace_id` and `span_id` to every audit record when present in the supervisor's environment. With that change every row above gains a Timing and Relationship link to the framework's spans, and the runtime record becomes joinable to an OTel trace by trace ID rather than by timestamp.

This is the one change that turns an enforcement-point record from a parallel evidence store into a participant in the WG's trace model.

## 6. Open questions for reviewers

1. Should `enforcement_layer` (kernel | broker | proxy) be a column, or a value in the Provenance cell, so that the absence of kernel-originated events is explicit rather than implied?
2. Is a runtime that decides and enforces the correct observer-of-record for the HITL row, or should the HITL row belong to the approval backend's own telemetry, with the runtime record cited as corroboration?
3. Do these rows want a "declared vs granted vs used" triple as a standard Security sub-structure, given both the CLI deep-dive and this one arrive at it independently?
