# Agent → MCP Server Boundary Deep-Dive

**Status:** First filled matrix pass, ready for WG review
**Date:** 2026-08-19
**Owner:** Empire Labs Pty Ltd (Security Division), per issue #29
**Inputs:** working-documents/cross-boundary-observability-model.md (PR #25), working-documents/PRIOR-WORK.md

## 1. Purpose

This document delivers the Agent → MCP Server row for the cross-boundary observability model, per issue #29 and the gap-analysis work package (draft matrix Section 8, step 4: "produce a first filled matrix pass with citations to prior-work sources").

The Agent → MCP Server boundary is the most operationally common protocol boundary in agentic systems today: MCP is now governed by AAIF under the Linux Foundation, with 97M+ monthly SDK downloads and 10,000+ active public servers (mcp-evidence-validator README). It is also one of the least observable in practice: the declared contract (tool schemas, server manifest, annotations) and observed runtime behavior can diverge, and the divergence is usually invisible at the client.

For each matrix field we state: what should be observable, what existing efforts already cover, and what remains open. Coverage is assessed against the landscape documented in PRIOR-WORK.md plus the MCP protocol specification.

## 2. Boundary description

MCP is a JSON-RPC 2.0 protocol between an MCP client (the agent side) and an MCP server (the tool/data side), over stdio or Streamable HTTP transport. The interaction lifecycle is well defined by the spec:

- initialize handshake (protocol version negotiation, client/server capabilities)
- discovery (tools/list, resources/list, prompts/list)
- invocation (tools/call, resources/read)
- shutdown or error

OTel GenAI's MCP semantic conventions already model the canonical trace for this boundary (PRIOR-WORK.md):

```
invoke_agent weather-forecast-agent (INTERNAL)
 |-- chat {model} (CLIENT)
 |-- tools/call get-weather (CLIENT)          # MCP client
     |-- tools/call get-weather (SERVER)      # MCP server
 |-- chat {model} (CLIENT)
```

This gives us a shared vocabulary: client-side spans and server-side spans, correlated via W3C trace context in `params._meta.traceparent`.

## 3. Filled matrix row

| Field | Proposal | Coverage today | Open gap |
| :-- | :-- | :-- | :-- |
| Identity | Agent instance ID + principal; MCP server identity (URL, session, manifest); protocol version; auth method (bearer, OAuth, none) | Protocol-level: MCP session ID, clientInfo/serverInfo (spec); mcp.session.id (OTel GenAI) | Agent instance ID and acting principal are not standardized at this boundary; server manifest identity (which .mcp.json, which remote URL) is implementation-specific |
| Context | JSON-RPC request payload, session/state, exposed roots, capability negotiation results | W3C trace context propagation via params._meta.traceparent (OTel GenAI MCP conventions); MCP roots/capabilities negotiation (spec) | Full request context beyond traceparent; reconstructing session state at the server after the fact |
| Relationship | Request → response correlation (request ID); tool call → server-side sub-operations; resource subscription links | JSON-RPC request IDs (spec); client/server span pairing (OTel GenAI) | Server-side sub-operations inside a single tools/call are invisible unless the server self-instruments; subscription links not modeled |
| Lifecycle | initialize → negotiated (version, capabilities) → tools/list, resources/list, prompts/list → tools/call → shutdown or error | MCP lifecycle states (spec); mcp.method.name + mcp.session.id + session duration metrics (OTel GenAI) | No structured lifecycle event signal per session; failure modes (timeouts, partial responses, protocol errors) not consistently captured |
| Outcome | Result content, isError flag, server-side side effects, latency and token cost | isError flag + result (spec); span attributes + duration metrics (OTel GenAI) | Server-side side-effect manifest (files, APIs, resources touched) is not covered; token cost at server side |
| Provenance | Server manifest source (.mcp.json location, plugin origin, remote URL), version, transport (stdio vs Streamable HTTP) | serverInfo name/version (spec) | Manifest source and pinning are not standardized: where the contract came from and whether it mutated under the client is invisible; no contract-hash standard |
| Security | OAuth scopes granted, PKCE state, callback binding, sandbox level of the spawned server process, declared vs observed permissions | MCP authorization via OAuth 2.1 (spec); PKCE + callback binding (spec) | Declared vs observed permission usage is open: a server can declare read-only and write anyway, and the client cannot see it; consent-chain observability (granted scope → used scope) is not captured by any standard |
| Timing | Per-stage duration (initialize, negotiation, call, streaming), deadline/expiry behavior | Session duration metrics (OTel GenAI) | Per-stage timing breakdown across the boundary; propagation of deadline/expiry metadata |
| Evidence integrity (WG addition from our scoping comment) | The observation itself must be trustworthy: tamper-evident, hash-chained, append-only, attributable to the recording component | Nothing in the standards landscape; closest is OTel eBPF environment-derived telemetry (PRIOR-WORK.md), which is trusted network/runtime signal, not an evidence ledger | The full gap: no standard defines an evidence record for observability at any agentic boundary. This is the piece most standards efforts leave implicit |

## 4. Coverage summary

Covered at protocol level: identity (partial), relationship (correlation), lifecycle (states), outcome (isError/result), security (auth mechanism).

Covered at telemetry level: lifecycle timing, span correlation, session metrics.

**Open gaps (the load-bearing ones):**

1. **Declared vs observed (Provenance + Security).** The recurring blind spot across the boundary: what a server declared it could do (manifest, tool schemas, annotations, permission scope) versus what it actually did (side effects, scopes used, contract mutations). No standard captures this reconciliation. This is the measurement finding that matters most for governance.
2. **Evidence integrity.** No standard produces a tamper-evident record of boundary observations. Without it, provenance and security fields are claims, not evidence (our scoping comment, 2026-08-14).
3. **Server-side side-effect manifest.** Outcome is defined as result content, but what the server actually changed is not observable from the client.
4. **Consent-chain observability.** OAuth mechanism exists; recording granted scope → actually used scope does not.

## 5. Worked example: declared-vs-observed at this boundary

We operate a public reference implementation for gaps 1 and 2: [mcp-evidence-validator](https://github.com/narko4u/mcp-evidence-validator) (Apache-2.0, Python 3.10+ stdlib only, OpenSSF Best Practices project 14122).

What it does, mapped to the matrix fields:

1. Captures declarations: the tool schemas, permissions, and annotations an MCP server publishes (Provenance: manifest source + contract hash).
2. Observes reality: the tool invocations, argument shapes, and contract hashes seen at runtime (Outcome + Context).
3. Checks the gap: is a declared annotation still bound? Has the contract mutated since declaration? Is privilege use inside the declared scope? (Security: declared vs observed).
4. Produces a tamper-evident ledger: every check result is committed to a SHA-256 hash chain; changing any earlier record invalidates every record after it (Evidence integrity).

Concrete scenario: a server declares `readOnlyHint: true` on a tool. Later its contract is updated to add a mutating operation. A client that caches the original annotation will keep treating the tool as read-only, while the server now accepts writes. The validator detects the contract-hash mismatch at the next invocation and records the divergence in the evidence chain: the client now has a tamper-evident record that the declaration it relied on was stale as of a specific invocation. This is exactly the "annotation can be accurate at declaration time and silently stale minutes later" failure mode from the validator README.

The same evidence-chain pattern generalizes to the whole matrix: any of the eight fields can be recorded as claims, and the evidence ledger is what makes them auditable after the fact. WitnessOS (public spec: [narko4u/witnessos](https://github.com/narko4u/witnessos)) applies the same principle at the gateway: an agent requests an action, a human approves exact bytes, the gateway executes with held credentials, and anyone can verify the evidence chain afterward.

### 5.1 The declared side: ACI manifests and AIP contracts

The declared-vs-observed gap has two halves. The observed half is covered by the validator above. The declared half needs a standard way to express what a component declares: identity, capabilities, context fields, and security posture.

- **ACI (Agent Communication Interface)** is an open standard for agent communication manifests (repo: [narko4u/aci-spec](https://github.com/narko4u/aci-spec), CC BY 4.0 / MIT dual license). An ACI manifest declares identity, capabilities, permissions, and provenance in a machine-readable form, authored in AJSON (a superset of JSON that compiles to canonical JSON). It gives the Identity, Provenance, and declared Security fields of the matrix a concrete, publishable shape: the manifest is what gets pinned and hash-checked.
- **AIP (Agent Interaction Protocol)** layers interaction contracts and negotiation flows above ACI (Go module: [narko4u/aip-spec](https://github.com/narko4u/aip-spec)). A contract defines what an interaction is allowed to do before it happens: parties, allowed transitions, and the relationship (delegation, invocation, subscription) between them. This gives the Lifecycle and Relationship fields a declarative home: the contract is the agreed lifecycle, and deviations from it are observable events.

Together with the validator, ACI + AIP form the closed loop: declare (ACI manifest, AIP contract) → observe (validator) → verify (contract-hash check) → evidence (SHA-256 ledger). Both specs are open with public implementations (aci-validate CLI, aip Go module) and pass OpenSSF Best Practices at the top tier (baseline-1/2/3 all 100%, tiered score 300), matching the validator's badge profile.

## 6. Recommendations

Ordered by coordination effort, per the charter's coordinate-first principle:

1. **Feed the open gaps into existing venues rather than new standards.**
   - OTel GenAI SIG: propose MCP lifecycle event signal + server-side sub-operation spans (closes Lifecycle/Outcome relationship gap).
   - OTel GenAI SIG: propose contract-hash / declared-vs-observed attributes on MCP spans (closes Provenance/Security gap).
   - A2A/AGNTCY Observe: consent-chain and downscoped-auth observability (closes Security gap), consistent with our issue #29 scoping answer (2026-08-17).
2. **Evidence integrity as a cross-cutting matrix property.** Rather than one row, add it as a property applicable to every boundary, with a reference implementation pattern (SHA-256 hash chain ledger) so the conformance checklist can score it.
3. **Conformance checklist candidate** (matrix Section 7.2): declared-vs-observed checks become scorecard items: "server manifest pinned?", "annotation binding verified at runtime?", "evidence chain produced for boundary records?".
4. **Declared-side standards as candidates.** The gap analysis identifies what is missing; open standards with working implementations can fill it. ACI (manifests) and AIP (interaction contracts) are candidate declaration-layer standards, with public implementations (aci-validate, aip Go module) available for conformance testing. Evaluating them as the declaration layer of the closed loop (declare → observe → verify → evidence) is a concrete, low-cost next step, and both are in public feedback windows until 2026-09-15.

## 7. Open questions for WG review

1. Does evidence integrity belong as a property per boundary, or as a cross-cutting concern in the model (Section 3 of the draft)?
2. Should the Agent → Human (HITL) boundary be added to the seed matrix? We proposed it in the PR #25 matrix comment (approval, rejection, escalation events are observability-critical for accountability).
3. Should the Timing column be added to the seed matrix (Section 5 of the draft lists fields including timing, but the table omits the column)?
4. Is the declared-vs-observed gap genuinely unsolved elsewhere, or is a vendor already handling it that the landscape refresh should capture?

## 8. Suggested next steps

1. WG leads review this pass on the call (3 AM AEST Thu) or async.
2. If accepted, merge the filled row into working-documents/cross-boundary-observability-model.md (PR #25 follow-up or direct edit).
3. Convert the open gaps into upstream action items per Section 6.

---

Empire Labs Pty Ltd (Security Division) | contact@empirelabs.com.au
