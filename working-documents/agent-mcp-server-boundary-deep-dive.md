# Agent → MCP Server Boundary Deep-Dive

**Status:** Requirements-and-gaps pass, reworked for the chair review of 2026-09-26; ready for re-review

**Last updated:** 2026-09-28

**Inputs:** [cross-boundary observability model (PR #25)](https://github.com/aaif/wg-observability-and-traceability/pull/25), [PRIOR-WORK.md](./PRIOR-WORK.md), the [MCP specification (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28), and the [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)

## 1. Purpose

This document delivers a first filled matrix pass for the **Agent → MCP Server** boundary requested in [issue #29](https://github.com/aaif/wg-observability-and-traceability/issues/29), following the gap-analysis work package (draft matrix Section 8, step 4: "produce a first filled matrix pass with citations to prior-work sources").

The canonical matrix row is the semantic **Agent → MCP Server** relationship. Its protocol realization is the **MCP Client → MCP Server** boundary described in Section 2. The two are related but not interchangeable, in the same way the merged [Agent → Tool pass](https://github.com/aaif/wg-observability-and-traceability/blob/main/working-documents/agent-tool-cli-boundary-deep-dive.md) separates the semantic boundary from the operational process boundary that realizes it.

This pass identifies:

- which field semantics are already standardized at this boundary, and which are not;
- which propagation carrier carries each field across the boundary (protocol field, trace context, manifest, or nothing);
- what existing efforts cover today versus what remains open;
- which gaps are properties of the boundary as a whole rather than fields within it; and
- which remaining gaps should be coordinated with existing standards efforts rather than solved here.

MCP is now hosted by AAIF under the Linux Foundation ([PRIOR-WORK.md](./PRIOR-WORK.md)).

This pass states requirements and gaps at the boundary. It does not name, recommend or evaluate any specific implementation. No project is named except where the Working Group has independently selected one. The worked scenario in Section 5 is generic for that reason: it is written to hold for any implementation that satisfies the field table.

## 2. Boundary description

The reference shape:

```text
agent turn / invocation
  └── host application, runtime, or gateway      ← may or may not itself be the MCP client
      └── MCP Client  →  MCP Server              ← protocol boundary (this document)
          └── server-side sub-operations
```

The protocol boundary is **MCP Client → MCP Server**: a JSON-RPC 2.0 conversation over stdio or Streamable HTTP transport. The initiating agent and the represented principal remain important identity and context fields carried across this boundary, but **the agent may not itself be the MCP client**. The client role is frequently filled by a host application, an agent runtime, a gateway, or a sub-component of a larger agent. Describing this as "Agent → MCP Server" is useful as a matrix label for the semantic relationship; it is not a claim about which process speaks the protocol. Observations attributed to "the agent" at this boundary should therefore name the client as a distinct, resolvable identity wherever the two differ.

### 2.1 Session lifecycle and request lifecycle are separate

The specification defines these as distinct concerns, and they should be instrumented separately:

1. **Session lifecycle** — once per connection: `initialize` handshake (protocol version and capability negotiation), then an operational period, ending in shutdown or transport error. Session-scoped facts include negotiated protocol version, `clientInfo`/`serverInfo`, capability set, and session identity.
2. **Request lifecycle** — once per JSON-RPC request, independent of session: request issued, server-side handling, response or error; streaming responses and subscriptions extend a single request over time. Request-scoped facts include method name, request ID, parameters, result or error, and per-request duration.

Conflating the two is a common instrument error with observable consequences. A session can be healthy while individual requests fail or are retried; conversely a session-level failure must not be reported as a per-request outcome. Session duration is not a substitute for per-request latency, and a per-request error does not invalidate session-scoped negotiation facts recorded earlier. The matrix rows below state which lifecycle each field belongs to.

OTel GenAI's MCP semantic conventions already model the canonical trace for this boundary ([PRIOR-WORK.md](./PRIOR-WORK.md)):

```
invoke_agent weather-forecast-agent (INTERNAL)
 |-- chat {model} (CLIENT)
 |-- tools/call get-weather (CLIENT)          # MCP client
     |-- tools/call get-weather (SERVER)      # MCP server
 |-- chat {model} (CLIENT)
```

This gives a shared vocabulary: client-side and server-side spans, correlated via W3C trace context carried in `params._meta.traceparent`.
## 3. Filled matrix pass

For each field this pass separates three things the review asked to keep distinct:

- **Field semantics** — what the field means at this boundary and what must therefore be observable.
- **Propagation carrier** — the mechanism that actually carries that meaning across the boundary (a protocol field, trace context, a manifest, an out-of-band record, or nothing at all). A field can be well understood semantically and still have no carrier capable of moving it across the boundary.
- **Implementation coverage** — what existing efforts already emit, versus the open gap. Coverage is assessed against [PRIOR-WORK.md](./PRIOR-WORK.md) and the MCP specification.

| Field | Semantics: what must be observable | Propagation carrier | Implementation coverage / open gap |
| :-- | :-- | :-- | :-- |
| Identity | Who: client (which is not necessarily the agent), agent instance, represented principal, server identity, protocol version, auth method | Session-scoped protocol fields: `clientInfo`, `serverInfo`, negotiated protocol version, session ID; transport-level auth (OAuth 2.1 bearer, PKCE) | `mcp.session.id` and `clientInfo`/`serverInfo` are standardized at the protocol level; agent instance ID and acting principal have no standard carrier at this boundary, and server manifest identity (which config file, which remote URL) stays implementation-specific |
| Context | The circumstances of the call: request parameters, session state, exposed roots, negotiated capabilities, deadline and budget | Request-scoped: JSON-RPC `params`; session-scoped: `initialize` result (roots, capabilities); cross-cutting: W3C trace context in `params._meta.traceparent` | Trace context propagation is standardized (OTel GenAI MCP conventions); capabilities and roots are negotiated in-session; deadline, budget and policy context have no common carrier at this boundary |
| Relationship | How observations join up: request → response correlation, client span → server span pairing, tool call → server-side sub-operations, subscription lifetime | Request ID pairing in the JSON-RPC envelope; W3C Trace Context for parent/child causality and span links for detached or background work | Request IDs correlate a call with its response, and client/server span pairing is modeled by OTel GenAI; server-side sub-operations inside one `tools/call` remain invisible unless the server self-instruments; subscription relationships are not modeled |
| Lifecycle | Both lifecycles, separately: (session) initialize → negotiated → operational → shutdown or error; (request) issued → handled → result or error → streamed/subscribed | Session state and negotiated capabilities in the protocol; method name and duration through telemetry (`mcp.method.name`, session duration metrics) | Protocol states are specified, but no structured session event signal exists, and per-request stages (queue, handler, stream) are not distinguishable in current telemetry; session and request outcomes are routinely conflated |
| Outcome | What happened: result content, `isError`, partial or streamed results, server-side side effects, latency and cost | Method result and `isError` in the JSON-RPC response; duration and result-size telemetry attributes | `isError` and result presence are specified and instrumented; what the server actually changed (files, APIs, resources, downstream calls) has no carrier at all, and cost is not attributable at the server side |
| Provenance | Where the contract came from and whether it held: manifest source, version, contract hash, transport, observer identity | Out of band: the server manifest and its location; `serverInfo` name/version in the protocol; nothing in-band for the manifest itself | `serverInfo` carries name and version only. Manifest origin, pinning, and whether the contract mutated under the client are not standardized, and there is no contract-hash field to carry the answer |
| Security | Authorization actually exercised: scopes granted and scopes used, PKCE and callback binding, sandbox level of the spawned server process | Authorization metadata in the protocol; OAuth 2.1 grant state out of band at the authorization server | OAuth 2.1 with PKCE and callback binding is specified. Recorded reconciliation of granted scope against used scope has no carrier, so a server that declares read-only and then writes is invisible to the client |
| Timing | When, at what cost, and under what budget: per-stage duration, deadline propagation, expiry behavior | Telemetry duration attributes; deadline metadata in the request envelope | Session duration metrics exist; per-stage timing across the boundary is missing, and deadline/expiry metadata is not propagated in a standardized way |
### 3.1 Cross-cutting properties, not additional fields

Two properties apply to every field above rather than occupying a field of their own, following WG review on PR #32:

1. **Evidence integrity** — whether a boundary record is trustworthy at all: tamper-evident, integrity-protected in a way that is verifiable after the fact, effectively append-only, and attributable to the component that recorded it. A field can be captured correctly and still be worthless as evidence if the record can be altered afterwards without detection. Nothing in the standards landscape defines this for agentic boundaries; the closest existing signal is environment-derived telemetry, which is trusted runtime observation rather than a verifiable record ([PRIOR-WORK.md](./PRIOR-WORK.md)). This property applies uniformly to all eight fields above; it is not a ninth field.
2. **Declared-versus-observed reconciliation** — whether what a component declared (manifest, tool schemas, annotations, permitted scope) still matches what it actually did. This is a comparison between fields rather than a field: it consumes the declared side (Provenance, and the granted half of Security), the observed side (Outcome, and the used half of Security), and yields a verdict. The verdict is what a governance consumer acts on, so it belongs as a property of the boundary, alongside the field table that supplies its inputs.

### 3.2 Capture qualifications for request and result payloads

Any capture of request or result payloads under Context and Outcome is subject to four qualifications. They are constraints on the capture, not optional refinements, because a boundary record is often retained longer and read by more people than the traffic it records:

- **Minimization.** Default to structural metadata — method name, argument names and shapes, counts, byte lengths, hashes — rather than content. Content capture is opt-in per deployment, consistent with the treatment in [issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42)'s kit and with GenAI conventions that make content capture opt-in.
- **Redaction before persistence.** Redaction happens before the record is written, never in downstream tooling or at read time. A record that once contained a credential cannot be un-leaked by filtering a view of it. Redaction must also be recorded as having occurred, without recording the redacted value.
- **Access control on the record itself.** A captured payload carries its own authorization requirements: a record inherits at least the sensitivity of the traffic it captures, and recording must not widen the set of parties who can read it. Structured metadata and captured content need not share one access policy.
- **Capture-policy attribution.** The record states which capture policy produced it (metadata only, sanitized arguments, hashes only, content captured). Without that attribution a consumer cannot distinguish a field that was absent from one that was denylisted or never captured — which changes how the record should be read.

### 3.3 Evidence grades are established by the consumer, not the producer

An evidence grade states what a record must demonstrate to be read at that level; it does not state who establishes the level. If a consumer reads a grade off a record and repeats it, the grade is a producer claim about the producer's own evidence and carries no independent weight. One normative line therefore belongs wherever the grades are defined:

> A consumer MUST NOT report a record at a grade whose required properties it has not itself re-derived from the record and from the external parties those properties name.

The companion fixture pair, two records identical in every producer-authored field where the externally issued material verifies in one and fails in the other, is a natural fit for the kit in [issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42). The pair is filed as [PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57).

## 4. Coverage summary

Covered at protocol level: identity fields that are session-scoped (client and server info, negotiated version, session ID), request/response correlation, session lifecycle states, outcome presence and error flag, and the authorization mechanism.

Covered at telemetry level: client/server span correlation, method names, session duration metrics.

**Open gaps, in the order they block a conforming record:**

1. **Declared versus observed (§3.1).** The declared side (Provenance, granted scope) and the observed side (Outcome, used scope) are each partially observable, but nothing carries the comparison, so the verdict a governance consumer needs does not exist in any standard.
2. **Evidence integrity (§3.1).** No standard produces a verifiable record of boundary observations. Absent this, every other field is a claim rather than evidence.
3. **Server-side side effects (Outcome).** Outcome is defined by result content and error status, while what the server actually changed — files, APIs, resources, downstream calls — is invisible to the client and uncarried.
4. **Consent-chain observability (Security).** The authorization mechanism is specified; recording granted scope against used scope is not, so consent is observable at grant time only.
5. **Session and request lifecycle conflation (Lifecycle).** Current instrumentation does not reliably separate session-scoped facts from per-request outcomes, and per-request stages (queued, handling, streaming) are indistinguishable.

## 5. Worked scenario

The gaps above are easier to read as one scenario. It is deliberately generic: it names no product, and every fact in it is available from the protocol or from the existing telemetry conventions, so it holds for any implementation that satisfies the field table in Section 3.

A client opens a session with a server and negotiates version and capabilities (Section 2.1). The server publishes a tool contract carrying four things: a name, an input schema, a required scope and an annotation marking the tool read-only. The client caches the contract and calls the tool.

1. **Session and request are instrumented separately.** The session carries `clientInfo`, `serverInfo`, negotiated version and session ID. The request carries its parameters, its request ID and trace context. A session can stay healthy while a request stalls, is retried or fails, so a session-level reading is a wrong answer to a request-level question.
2. **The response is observable, the effect is not.** The client sees a result and `isError: false`. What the server changed while producing that result, whether it touched files, APIs, resources or downstream systems, is not carried back at all, so the observed half of the boundary is incomplete by construction rather than by a gap in instrumentation.
3. **Declaration and use are observed by different parties.** The client knows which tool it called and which scope it granted. It does not know which revision of the contract the server is serving, and it does not know which scope the call exercised. Both facts exist, neither is carried in a form the client can bind to the call.
4. **The stale declaration.** The read-only annotation was accurate when the contract was published. Later the contract gains a mutating operation and the client keeps applying the cached annotation, so a consumer reading the client's record sees a read-only tool performing writes. Nothing in the record marks the moment the declaration became stale.
5. **Nothing above is verifiable afterwards.** Even where a field is captured correctly, an environment-derived telemetry record is a trusted runtime observation rather than a record whose integrity survives the component that wrote it. The result is a set of claims about the boundary rather than evidence about it.

Every gap in Section 4 appears in this scenario as a missing carrier rather than a missing concept. What the WG decides is where each missing half is carried: a protocol extension, a telemetry attribute, or an out-of-band record whose integrity is verifiable after the fact (Section 3.1).

## 6. Recommendations

Ordered by coordination effort, per the charter's coordinate-first principle:

1. **Feed the open gaps into existing venues rather than proposing a new standard.**
   - OTel GenAI SIG: a session event signal distinct from per-request spans, plus per-request stage attribution (closes Lifecycle gap 5).
   - OTel GenAI SIG: contract-hash and declared-versus-observed attributes on MCP spans, carrying the §3.1 comparison (closes gaps 1 and 3 partially).
   - AGNTCY Observe / A2A: consent-chain observability, granted scope against used scope (closes gap 4).
   - [Issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42)'s kit, which now takes the §3.3 fixture pair in [PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57): re-derivation checks.
2. **Record the two cross-cutting properties in the model, not in the field table.** Evidence integrity (§3.1) and declared-versus-observed reconciliation apply to every boundary and should appear as properties of the model with clear scope, so the per-boundary tables stay about fields.
3. **Add the review's distinctions to the matrix template.** Field semantics, propagation carrier, and implementation coverage should be separate columns in every filled pass, so a row cannot imply that an understood field has a working carrier.
4. **Conformance checklist candidates** (matrix Section 7.2): is the server manifest pinned? is annotation binding verified at runtime? is an integrity-protected record produced for boundary observations? is the capture policy attributed on the record? are session-scoped and request-scoped outcomes reported separately?

## 7. Open questions for WG review

1. Where do the two cross-cutting properties live in the model — a properties section, or annotated per boundary?
2. Does the capture qualification set in §3.2 belong in the model (applying to every boundary that captures payloads), or only in per-boundary passes?
3. Should the Agent → Human (HITL) boundary be added to the seed matrix? It was proposed in the [PR #25](https://github.com/aaif/wg-observability-and-traceability/pull/25) matrix comment — approval, rejection, and escalation events are observability-critical for accountability.
4. Should the Timing column be added to the seed matrix? Section 5 of the model draft lists timing among the fields, but the table omits the column.
5. For the declared half of the comparison, what carrier should the WG prefer: a manifest format, protocol-level extension fields, or an existing in-flight AAIF work item? The answer may differ per field.
6. Is the declared-versus-observed gap genuinely unsolved elsewhere, or is a vendor already handling it that the landscape refresh should capture?

## 8. Next steps

1. WG leads review this revision on the call or async, alongside the unresolved questions in Section 7.
2. Once the cross-cutting properties are placed, fold the filled row into [the model (PR #25)](https://github.com/aaif/wg-observability-and-traceability/pull/25) rather than keeping a parallel copy.
3. Reconcile §3.3 with [PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57), which files the fixture pair for [issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42)'s kit: two records identical in every producer-authored field, where the externally issued material verifies in one and fails in the other.
4. Carry the coordinate-first asks in Section 6 to OTel GenAI SIG and AGNTCY Observe.
