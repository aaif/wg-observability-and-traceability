# Agent identity in telemetry: the accountable principal

**Status:** Draft for WG review, contribution to [issue #50](https://github.com/aaif/wg-observability-and-traceability/issues/50); the redaction rules (section 4) are co-owned with Security & Privacy and await its review

**Last updated:** 2026-11-12

**Inputs:** the agent identity attribute table and redaction rule proposed in #50; the [cross-boundary observability model](./cross-boundary-observability-model.md) (Agent -> Agent row: "principal each represents"); the I&T Reference Architecture draft (V1, 2026-10-21); [OpenTelemetry attribute requirement levels](https://opentelemetry.io/docs/specs/semconv/general/attribute-requirement-level/); [W3C Baggage](https://www.w3.org/TR/baggage/) and the [OpenTelemetry baggage guidance](https://opentelemetry.io/docs/concepts/signals/baggage/)

This section adds one attribute group, `agent.accountability.*`, to the agent identity attributes proposed in #50, and four redaction rules to the rule proposed there. It does not name, recommend or evaluate any implementation. Attribute names and namespace are provisional, to be aligned with the OpenTelemetry GenAI conventions before any upstream proposal.

## 1. Attribution and accountability

Attribution answers which agent acted, under which issuer and which grant. Accountability answers which principal answers for the action. `agent.id`, `agent.issuer` and `agent.grant_id` answer the first question; none of them answers the second, and `agent.principal.type` with human / workload / service mixes the two. A workload can be the principal an agent acts for, but the party that answers for the action is a natural or legal person. The I&T Reference Architecture draft (V1) draws the same line: a relying party must never read a delegation chain as an accountability chain, and it verifies that the accountable parties exist at a stated assurance level without necessarily learning who they are.

The table needs the distinction because the boundary matrix already asks, at Agent -> Agent, for the principal each party represents, and because the cases #50 is to trace (a refusal, a revocation after dispatch) turn on whether an accountable principal stood behind the agent when the action was decided, not only on which agent it was. Telemetry cannot carry the principal: an identifier of the person in spans, metrics or baggage is personal data at every backend the trace reaches, and a correlation handle for that person at every party that sees it. What telemetry can carry is a reference to the check a deciding party made, with its result. The reference resolves only in that party's own audit store, so the trace stays a correlation record and the evidence stays where it was produced.

The attributes and rules below serve one property: every party in a chain can verify that an accountable principal stands behind the agent, and that it is the same principal throughout the chain, without any party other than the issuer of an identifier being able to link that principal across trust domains. The issuer retains the mapping and resolves it on a legitimate request, under a stated process, when an audit or a dispute requires it. This is the reading that makes audit compatible with data minimisation and purpose limitation.

## 2. Attributes

These attributes are set on the span of the operation that an accountable-principal check gated (a request, a tool call, a dispatched task), by the party that made the check (the deciding party). A party that relies on another party's check without making its own does not set them (rule 3).

| Key | Stability | Requirement Level | Value Type | Description | Example Values |
| --- | --- | --- | --- | --- | --- |
| `agent.accountability.result` | Development | `Conditionally Required` If the operation was gated by a check that an accountable principal stands behind the agent. | string | The result of the deciding party's check that an accountable principal stands behind the agent. [1] | `verified`; `refused`; `not_evaluated` |
| `agent.accountability.ref` | Development | `Conditionally Required` If `agent.accountability.result` is set and the deciding party wrote a record of the check. | string | Reference to the deciding party's own record of the check, resolvable only in that party's audit store. [2] | `effa2870801ea4b6a9eee4021cf7f9355a4f2d97ad4ad8ec29efd8d47791e08e` |
| `agent.accountability.assurance` | Development | `Recommended` If the check required an assurance level. | string | The assurance level the check required of the verification of the accountable principal. [3] | `substantial`; `high` |

`agent.accountability.result` has the following list of well-known values. If one of them applies, the respective value MUST be used.

| Value | Description | Stability |
| --- | --- | --- |
| `verified` | The check completed and the evidence met the requirement: an accountable principal stands behind the agent at the required assurance level and within the required scope, and the status information the check relied on was within the age bound the deciding party had declared. | Development |
| `refused` | The check completed and the evidence did not meet the requirement: no accountable principal was shown, the assurance level or the scope fell short, or the status information the check relied on showed the authority withdrawn. | Development |
| `not_evaluated` | The check did not complete (the evidence or the status information could not be obtained or proven at the decision). It is not a refusal of the principal. What happens to the operation is the deciding party's policy; a fail-closed policy does not run it. | Development |

**[1]** The result describes the check, not the operation. An operation can still be refused for another reason after a `verified` check; the operation's own outcome stays in the span's status and its other attributes. If the `agent.accountability.*` attributes are absent, no check gated the operation: the group does not apply to it, which is what the `Conditionally Required` level states. `not_evaluated` means that a check was required and did not complete. Absence and `not_evaluated` are kept apart in the same way as an evidence run keeps `not_applicable` apart from `not_measured`. `refused` and `not_evaluated` are kept apart so that a trace distinguishes an agent with no accountable principal from a check that could not complete. Three values: low cardinality, usable as a metric attribute.

**[2]** The value is opaque to every reader except the deciding party (a digest of the record or an identifier the deciding party assigns to it; open question 1). It is unique per decision and therefore high-cardinality: spans and logs only, never a metric attribute. It is derived from nothing presented to the deciding party, it is never the same at two relying parties (rule 1), and it is not propagated (rule 3). It is exported only to telemetry backends inside the deciding party's trust domain; a backend run by a third party receives the span without it.

**[3]** The value names a level, never the evidence that met it (rule 2). No level vocabulary is fixed yet by this WG or by the I&T Reference Architecture (open question 2); until one is, the value is the level as the deciding party's policy names it, for example a level of assurance of an established scheme. Low cardinality, usable as a metric attribute together with `agent.accountability.result`.

No attribute for the time of the check is proposed: the span's own timing places it, and the time of the decision and the age of the status information it relied on are in the record (section 3). Whether the age should also be in telemetry is open question 3.

## 3. The record behind the reference

The record belongs to the deciding party, stays in its audit store and is not published. Its format is the deciding party's; this list states only what it holds, so that a refusal or a revocation after dispatch can be judged from it.

- the result, and which rule of the deciding party's policy decided it;
- the time of the decision;
- the requirement the check was made against (assurance level, scope), or a digest that commits to it;
- the status or revocation information the decision relied on, named by values that are the same for every principal of the same issuer, and its age at the decision;
- the age bound that applied, as the deciding party declared it before the decision (the bound can live in the party's published policy rather than in each record);
- a digest of the context the check was bound to (the audience, the request, the operation), never the context;
- nothing presented to the deciding party: no credential, no attribute value, no identifier of the principal.

With these properties a revocation that happens after dispatch is judged against a bound stated in advance. A reviewer judges the decision by the status information it relied on and that information's age against the declared bound, not by the status at the time of the review. An operation decided `verified` on status information within its declared age bound was decided within the rules, and the revocation governs the decisions taken after it has taken effect. The question is answered from the record, by whether the decision met the rules it declared, not by comparing a relying party's clock with the time the revocation was requested.

## 4. Redaction rules

These add to the rule proposed in #50. They are written from the holder's side: the person or organisation behind the agent. Rule 1 is the base, and rules 2 and 4 follow from it: an attribute behind a check and a status handle are values that stay the same wherever the credential is presented. Rule 3 governs where the reference goes.

1. **No value that stays the same across relying parties or trust domains goes into spans, metrics or baggage.** The rule is on the value, not on the field: `agent.id` or `agent.grant_id` can be present, but a value of theirs that is the same at two relying parties cannot; a per-relying-party value at most. Such a value is a correlation handle for the person even when it names nobody. The rule concerns values tied to the agent, its credential, its grant or its principal; a value shared by every principal of an issuer, such as an issuer reference or an assurance level, is not such a handle. *Not this:* the same agent identifier, grant identifier, credential subject or holder key sent to every relying party the agent calls.
2. **The result of a check, and none of the attributes behind it.** Telemetry needs what was decided; the attributes are personal data at every backend the trace reaches. "Assurance level met", not the evidence, an age, a region or the credential. *Not this:* a date of birth or an age, a nationality or a region, the type or number of an identity document, a credential, a presentation or any part of one.
3. **The accountability reference does not travel in baggage across a trust boundary.** It stays with the party that made the check, and a downstream party that needs it makes its own check. Baggage reaches parties the sender does not choose and can be propagated outside the sender's network. The case to test first is the asynchronous hop: the deciding party makes the check and dispatches the task asynchronously to a service in another trust domain; `agent.accountability.ref` travels neither in the message nor in baggage; the downstream service, under its own policy, either makes its own check and sets its own attributes, or records the operation without `agent.accountability.*` (for that service no check gated it). *Not this:* `agent.accountability.ref` set as a baggage entry by the deciding party and recorded by a service in another trust domain as evidence of its own.
4. **No status or revocation handle in telemetry that would let a reader of the trace follow the credential at its issuer.** A handle of this kind lets anyone who can read the trace and the issuer's status information watch that credential (when it is suspended, renewed or revoked) without taking part in any decision. *Not this:* a status-list location with its index, a revocation identifier, a revocation witness, or the credential's serial number. The record names the status information by values shared with every principal of the issuer (section 3).

## 5. Open questions for the group

1. **What `agent.accountability.ref` is.** A digest of the record (anyone given the record can check that it matches, and the deciding party keeps no index), or an opaque identifier the deciding party assigns (nothing derived from the record leaves it, and the mapping can be deleted with the record)? In both cases it is unique per decision and never the same at two relying parties.
2. **Assurance levels.** Adopt an existing scheme by name (for example the eIDAS levels of assurance, ISO/IEC 29115 or the NIST SP 800-63 identity assurance levels), with the scheme named in the value, or wait for the I&T Reference Architecture to fix one? The shared assurance vocabulary raised in Security & Privacy for attestation evidence (how the evidence about an agent was produced) is a different axis and is kept apart from this one.
3. **Age in telemetry.** Is the span's own timing enough, with the age of the status information kept in the record, or should the table add an attribute for that age at the decision (low cardinality, the same for every principal of an issuer)? No such attribute is proposed here.
4. **Relation to a generic span-to-record reference.** [PR #67](https://github.com/aaif/wg-observability-and-traceability/pull/67) (seam 1, span to record join) proposes supporting [semantic-conventions-genai #239](https://github.com/open-telemetry/semantic-conventions-genai/issues/239) (opaque governance references) as a generic, digest-addressed record reference on `execute_tool` and `invoke_agent`, following the absolute-URI `_ref` pattern that [semantic-conventions-genai #490](https://github.com/open-telemetry/semantic-conventions-genai/pull/490) set for content. `agent.accountability.ref` is a reference of that kind with two limits: it does not resolve outside the deciding party, and it is not exported outside that party's trust domain (note [2]). Should the table state this as a difference from the `_ref` pattern, or adopt its syntax with both limits kept, if the group prefers one reference form?
