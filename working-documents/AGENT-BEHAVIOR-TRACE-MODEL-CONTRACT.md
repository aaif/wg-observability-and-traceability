# Agent Behavior Trace Model: shared contract

Status: Living working group document (v0.7-draft) - last revised 2026-09-21 (revision 7: applicability established by exported reference, not by counting decisions; unresolved-applicability report names only the decisions actually recorded)

This document is the draft shared contract for the Agent Behavior Trace Model workstream. It records which identities and relationships the two agent examples ([Task 2](https://github.com/aaif/wg-observability-and-traceability/issues/40)) should export, how those relationships should be interpreted, and how they map to AAIF terminology and OpenTelemetry. It follows the [execution plan](https://github.com/aaif/wg-observability-and-traceability/pull/48) and is tracked in [issue #41](https://github.com/aaif/wg-observability-and-traceability/issues/41).

Recording this draft does not make these semantics an adopted standard. Unresolved choices are collected in [section 9](#9-unresolved-choices) rather than silently decided. Once the Task 2 baselines are captured, the draft is expected to be revised against them before any version is proposed as a recommendation.

## 1. Purpose

The contract answers three questions for every exported record:

1. **What work does this record identify?** (identities, section 3)
2. **How does that work connect to other work?** (relationships, section 4)
3. **What may a consumer conclude from the records, and what must remain unknown?** (interpretation rules, section 6)

The four priority questions from the execution plan drive the scope:

- **Continuity:** which turns belong together, including after a pause or restart
- **Calls and retries:** which model calls served each turn, without counting the same work twice
- **Approvals:** which decision concerned an action, and did that action execute
- **Effects:** which external change can be connected to that execution

## 2. Reading rules

- **Contract identities** (for example `C1`, `T2`, `P1`) are illustrative fixture identities, not proposed OTel attribute names. This follows the convention in the task issues.
- **Contract terms** (Conversation, Turn, Proposed action, ...) are the versioned terms this document defines. Section 8 crosswalks each to AAIF taxonomy status.
- **Native labels** are what a given runtime calls the same thing (thread, session, chat, run). Each example maps its native labels to the contract identities in its own mapping file; mappings are declared, never assumed.

## 3. Identities

| Identity | Meaning | Fixture example |
| --- | --- | --- |
| **Conversation** | The user-visible continuity scope: the unit that survives pauses, restarts, and process boundaries. | `C1` |
| **Runtime session** | A transport- or runtime-level session (protocol session, process-local session object). A restart opens a new runtime session; the conversation continues. Distinct from Conversation and never merged with it. | `S1`, `S2` after restart |
| **Turn** | One user-initiated exchange within a conversation: request, the work it triggers, and the reply. | `T1`, `T2` |
| **Model call** | One logical inference operation, including any internal retries by the caller. | `M1` |
| **Proposed action** | A record that the agent proposed to perform an action with described arguments. Exists whether or not it is approved or executed. | `P1` |
| **Approval decision** | A human or policy decision on exactly one proposed action. Recorded when denied as well as when approved. A proposal may carry more than one decision over its lifetime; section 6 defines how they are read. | `A1` |
| **Tool execution** | The execution of an action through a tool. | `E1` |
| **External effect** | An independently observed change in the world, reported by a source outside the agent (for example a service-side receipt). | `ticket-42` receipt |
| **Agent trajectory** | The path of one agent instance across conversations. Named here for AAIF vocabulary alignment; not required by the four priority questions. | - |

Identity rules:

1. Identifiers are assigned by the system that owns the entity and are opaque to consumers.
2. No synthesized fallback identifiers. If a runtime owns no conversation id, the record carries none; it does not carry a new UUID, trace id, or content hash. This mirrors the OTel rule for `gen_ai.conversation.id`.
3. Records carry the native label and the contract identity together. The mapping replaces nothing; it annotates.
4. **Identity and correlation keys are scoped.** A key is only meaningful together with the scope of the system (and, where applicable, tenant) that issued it. The same ticket id observed in two services or two tenants denotes two distinct identities; their effects must not be merged. Joins (R1-R6) and receipt deduplication operate only within the same scope. The exported representation of the scope is an open choice (section 9, item 10).

## 4. Relationships

| # | Relationship | Meaning | How it is expressed |
| --- | --- | --- | --- |
| R1 | Turn → Conversation | Membership: which turns belong together. | Shared conversation identity. Never trace-tree ancestry or timestamps alone. |
| R2 | Model call → Turn | Service: which calls served a turn. | Reference from the call record to the turn it served. |
| R3 | Proposed action → Turn | Origin: within which turn the proposal was made. | Reference from the proposal to its turn. |
| R4 | Approval → Proposed action | Decision: which action a decision concerned. | Reference from the decision to exactly one proposal; present for denials too. |
| R5 | Tool execution → Proposed action | Realization: which proposal an execution carries out. | Reference from the execution to the proposal (and, where applicable, to the approval it followed). |
| R6 | Tool execution → External effect | Correlation: which observed change connects to which execution. One execution may produce multiple effects; the relation is one-to-many. | Correlation key shared between the receipt and the execution (for example the ticket id returned by the service and by the tool), qualified by the issuing scope (identity rule 4). |

Each relationship record carries: the source identity, the target identity, and the relationship kind. The record also carries **how the link was established** - the *method* - drawn from the named set `{span-link, attribute-reference, causal-flag, external-correlation-key}`. Examples may use additional methods, but interpretation rules are defined only for these four.

The method is **required on the record**, with one permitted relaxation: if an exporter is uniform - for example, an instrumentation library that always emits R1 through R5 as attribute references - the example's mapping file may declare a per-example default that covers the relationships where the field is omitted. A consumer resolves the method in this order:

1. The record's own method field, if it carries one of the four methods defined above.
2. The example's mapping-file default for the same relationship kind, if declared and applicable.
3. Otherwise: **the relationship is not established** for the purposes of this contract; the consumer reports a mapping loss rather than inferring a method.

Two boundary cases follow from this order:

- **A present but unrecognized method.** A value outside the four-method set does not satisfy step 1, and the consumer does not fall back to step 2 for it: a present-but-unknown value is not an omitted field. The relationship is reported as not established (a mapping loss), and the loss report preserves the unrecognized value.
- **The same relationship exported more than once.** Records that share source, target, and kind - including one exported as a span link and another as an attribute reference, the shape the crosswalk in section 7 invites - establish one relationship. The consumer records each exported method as an observed method of that relationship. Divergent methods are not a conflict: the method describes how the link was exported, not which link it is.

Consumers must not reconstruct a relationship that was not exported, except to report it as missing.

## 5. Turn boundaries

These are candidate rules, to be tested by the examples in Tasks 5 and 6, not existing OTel requirements.

1. **One trace per turn is the candidate standalone default.** A completed turn is a closed trace; continuity comes from identity (R1), not from an open session-long span.
2. **Turn-entry span.** Each turn trace opens with a turn-entry span that anchors the turn identity. Which span plays this role is an open choice (section 9, item 1).
3. **Caller context is preserved.** When an agent runs inside an existing caller trace, the turn must not break that context; the turn trace links to it rather than discarding it. The exact mechanism is an open choice (section 9, item 4).
4. **Approval waits.** A turn may suspend while awaiting an approval decision. The suspension is recorded; the turn is not closed by it.
5. **Resumption.** When work resumes (the next morning, after a process restart, in a new runtime session and a new trace), the resumed work joins the same conversation and turn. The later turn asking "what was the ticket number?" is a new turn of the same conversation.

## 6. Interpretation rules

Rules for consumers answering the four priority questions from exported records alone:

**Continuity.** Group turns by conversation identity (R1). Do not group by trace parent, process, or wall-clock proximity. Ordering must not depend only on timestamps or a single parent-child span tree, especially for concurrent, queued, suspended, or resumed work.

**Calls and retries.** A logical model call may contain failed attempts and one success (R2). Reported usage is counted once per logical call. Retries the runtime does not export remain unknown; they are not zero and they are not silently counted. A record may carry per-attempt usage counters, a per-logical-call total, or both; these are different aggregation levels, and a consumer must not sum across them. Without declared aggregation semantics, combining levels yields unknown, not an estimate.

**Approvals.** An approval decision refers to exactly one proposed action (R4). Two layers must be kept apart:

- **Expected enforcement is what the decision says:** an approval licenses the action; a denial states that the action must not proceed. It is policy, not observation.
- **Observed evidence is what the records show.** A reader that observes a tool execution referencing a proposal must preserve every record and report what the records show; which finding applies depends on the decision side:
  - **A denial established as applicable by the records:** the execution references the denial as the decision it followed (the R5 optional reference). Being the proposal's only recorded decision does not establish this by itself - the reference does. The records disagree, and the disagreement is the finding. The execution is not dropped because a denial "should have prevented" it; the inconsistency is reported.
  - **Applicability not established:** the execution references no decision as the one it followed - whether one decision or several is recorded. The report names the execution, the decisions actually recorded, unresolved applicability, and unknown enforcement: "execution observed; approval and denial recorded; applicable decision unresolved; enforcement unknown" when an approval and a denial are what the records hold. The report never names a decision that was not recorded - two approvals produce "two approvals recorded" - the execution is called inconsistent with none of the decisions, and every recorded decision stays visible.
  - **No decision recorded:** the decision governing the execution is unknown - not unapproved, and not approved - and the report says so.
- A denial with no execution observation does not establish enforcement; enforcement is unknown. A missing decision record likewise means the decision is unknown - not unapproved, and not approved. Observed approval is not proof of enforcement.

**More than one decision on a proposal.** R4 constrains the decision side - one decision refers to exactly one proposal - but does not cap how many decisions a proposal may carry. A proposal may accumulate several over its lifetime: a reconsideration, or decisions from different applicable policies. Each decision stands as a valid record; none displaces another, and **which decision currently applies is unresolved**: the consumer reports the multiplicity, preserves every decision, and must not select a winner - not by arrival order, not by timestamp, and not by counting, because records are read as a set. Two decisions are not by themselves a conflict: a conflict is records disagreeing about one observation, while two decisions are two policy events. If a tool execution is observed while applicability is unresolved, enforcement is unknown. Supersession semantics are an open choice (section 9, item 11).

**Effects.** An external effect correlates to a tool execution through a shared correlation key (R6).

- A missing observation is **unknown**, not zero and not success. A removed ticket-creation receipt makes the answer "creation unconfirmed," not "no ticket was created."
- A receipt delivered twice is **one** confirmed effect, not two. Consumers deduplicate by correlation key **within its issuing scope** (identity rule 4); the same key value under a different service or tenant is a different effect, not a duplicate.
- Delayed or reordered arrival must not change the answer. Records are interpreted as a set, not as a stream.
- Conflicting observations (two receipts that disagree, including conflicting receipts sharing one scoped identity) are reported as conflicts and remain visible, not resolved silently.
- A service-side receipt is correlation evidence, not cryptographic attestation.

## 7. OpenTelemetry crosswalk

Mapping of contract identities and relationships onto the OTel GenAI semantic conventions. All `gen_ai.*` attributes and spans below are at **Development** status. The reader mappings claim compatibility with the following pinned source revisions, not with whatever `main` holds at read time:

- `docs/gen-ai/gen-ai-spans.md` at [`be23fcc250f7`](https://github.com/open-telemetry/semantic-conventions-genai/blob/be23fcc250f7/docs/gen-ai/gen-ai-spans.md) (2026-09-16)
- `docs/gen-ai/gen-ai-agent-spans.md` at [`b06f7a2c840c`](https://github.com/open-telemetry/semantic-conventions-genai/blob/b06f7a2c840c/docs/gen-ai/gen-ai-agent-spans.md) (2026-09-10)

If the conventions change, this crosswalk is re-verified against the new revision and re-pinned through a revision of this document; a reader must not assume compatibility with an unpinned revision.

| Contract concept | OTel mapping | Notes |
| --- | --- | --- |
| Conversation | `gen_ai.conversation.id` on inference and agent spans | Conditionally set: only when the instrumented library natively owns an id, or the application provides one via context. No synthesized fallbacks (see identity rule 2). |
| Turn | One trace per turn (candidate default, section 5); no `gen_ai` turn attribute exists today | Turn identity is carried by the example's mapping; see the OTel [turn-entry discussion](https://github.com/open-telemetry/semantic-conventions-genai/issues/356). |
| Model call | GenAI client inference span: name `{gen_ai.operation.name} {gen_ai.request.model}`, kind `CLIENT` (`INTERNAL` acceptable in-process) | Automatic retries stay inside one span; usage via `gen_ai.usage.*` attributes. |
| Continuation between turns | `gen_ai.request.previous_response.id` where the provider supports it; `gen_ai.conversation.compacted` for compacted context views | Provider-specific; examples document availability. |
| Agent operations | Agent and framework spans: `create_agent`, `invoke_agent` (CLIENT or INTERNAL), `invoke_workflow`, `plan`; tool execution via the `execute_tool` operation span | Per the OTel GenAI agent spans conventions; an LLM call that produces a plan is a child of the `plan` span. |
| R1–R6 across traces | Span links plus shared identity attributes | Not parent-child, except where work is genuinely nested (the `plan` case above). |
| Proposed action, Approval decision, External effect | No OTel convention yet | Recorded as example-local spans/attributes through each example's mapping. Upstream proposals are [Task 9](https://github.com/aaif/wg-observability-and-traceability/issues/47), each backed by a concrete example. |

## 8. AAIF terminology crosswalk

| Contract term | AAIF taxonomy status | Native labels seen so far |
| --- | --- | --- |
| Conversation | Pending (definitions deferred by the taxonomy workstream; "Session" definition under discussion) | thread, session, chat, conversation |
| Runtime session | Pending; must stay distinct from Conversation in any taxonomy entry | session, connection |
| Turn | Pending; the plan proposes "interaction turn" as a term | turn, run, interaction |
| Proposed action, Approval decision, Tool execution, External effect | To be fed back into the taxonomy by this WG | proposal, approval, tool call, receipt |

Rules:

1. Contract documents use published AAIF terms where they exist and label pending terms as pending.
2. Each example documents its native labels and maps them to contract identities (an SDK that calls conversations "threads" says so in its mapping).
3. The crosswalk is coordinated through [issue #10](https://github.com/aaif/wg-observability-and-traceability/issues/10) and the AAIF Taxonomy & Landscape workstream. This contract is input to that crosswalk, not a definition source for the taxonomy.

## 9. Unresolved choices

1. **Turn-entry span.** Which span anchors the turn identity: the `invoke_agent` span, the first agent-owned span, or a dedicated span.
2. **Standalone default vs. caller trace.** How one-trace-per-turn composes with an agent embedded in an existing caller trace.
3. **Suspend/resume marking.** How an approval wait and a later resumption are recorded without a session-long span, so a consumer can distinguish suspended, resumed, and closed turns.
4. **Caller-context mechanism.** Span link to the caller trace versus parenting under it.
5. **Attribute names** for proposed action, approval decision, and external effect. Deferred to Task 9 upstream proposals, evidence first.
6. **Baseline revisions.** The Task 2 baselines ([#40](https://github.com/aaif/wg-observability-and-traceability/issues/40)) are not yet captured; identities and relationships here are expected to be revised against them.
7. **Conversation identity when a runtime owns none.** Whether the contract treats it as mandatory for examples, or conditional as OTel does.
8. **Usage deduplication across providers.** How usage is counted once when retries span providers or hidden retries are partially visible.
9. **Second agent/SDK.** Selection affects which native labels and resumption paths the first revision must cover.
10. **Representation of identity scope.** How the issuing scope of an identity or correlation key (service, tenant) is carried in exported records. The scoping rule itself (identity rule 4) is fixed; the attribute form is open and feeds the Task 9 upstream proposals.
11. **Supersession among decisions.** Whether and how a later decision on the same proposal supersedes an earlier one. The candidate mechanism is an explicit reference from the new decision to the one it replaces; arrival order and timestamps cannot do it, because records are read as a set. The reference needs a new attribute, so it follows the Task 9 discipline of item 5. Until it exists, multiple decisions on one proposal stand together with unresolved applicability (section 6, Approvals).

## 10. Fixture example

The support workflow from the execution plan, expressed in fixture identities. This is the shape the Task 4 test kit ([#42](https://github.com/aaif/wg-observability-and-traceability/issues/42)) is expected to turn into fixtures with expected answers.

| Record | Identity | Related to | Notes |
| --- | --- | --- | --- |
| User asks to look up the delayed order | `T1` | `C1` | First turn; model call `M1` serves it. |
| User requests a ticket | `T2` | `C1` | Model call `M2` fails once, retries, succeeds; usage counted once. |
| Agent proposes creating a ticket | `P1` | `T2` | Proposed action with ticket fields. |
| User approves | `A1` | `P1` | Approval decision, recorded as approved. |
| Agent executes the ticket tool | `E1` | `P1`, `A1` | Tool execution. |
| Test service records ticket-42 | receipt | `E1` | External effect; correlation key is the ticket id. |
| Next morning, user asks for the ticket number | `T3` | `C1` | New turn, new trace, possibly new runtime session; joins `C1` by identity. |

Expected answers for the degraded cases:

- Receipt delivered twice: still one confirmed ticket.
- Receipt removed: "creation unconfirmed," not "no ticket was created."
- `M2` failure exported, success missing: the call and its usage are unknown, not zero.
- A second, different service also returns a ticket id `42`: a distinct effect in its own scope; not merged with the `ticket-42` receipt above, not deduplicated against it.
- `M2` usage exported both per attempt and as a logical-call total, with no declared aggregation: combined usage is unknown; a consumer must not sum the levels.
- An execution is observed that references a proposal and the denial it followed (the denial is the proposal's only recorded decision, and the execution's reference establishes it as applicable): both records are preserved, the inconsistency is reported, and enforcement is unknown; the execution is not dropped.
- An execution references a proposal whose only recorded decision is a denial, but nothing establishes that the denial governed the execution: the report is "execution observed; denial recorded; applicable decision unresolved; enforcement unknown" - not an inconsistency.
- A relationship record carries source, target, and kind but no method field, and the example's mapping file declares no default for that relationship: the relationship is reported as not established (a mapping loss), not silently inferred.
- The same relationship is exported twice with the same source, target, kind, and method: it is one relationship, not two.
- A relationship record carries a method outside the four-method set while the example's mapping file declares a default for that kind: the relationship is still not established; the default is not applied, and the unrecognized value is preserved in the mapping-loss report.
- The same source, target, and kind exported once as a span link and once as an attribute reference: one relationship with two observed methods, not a conflict and not two relationships.
- A denial and an approval recorded on the same proposal, with nothing relating them: both decisions stand; which one applies is reported as unresolved; the pair is not a conflict.
- An execution is observed on a proposal that carries both an approval and a denial, with nothing relating them: all three records are preserved and the report is "execution observed; approval and denial recorded; applicable decision unresolved; enforcement unknown." The execution is not reported as inconsistent with the denial - that would assume the denial governed it - and the denial stays visible.
- Two approvals from different policies on the same proposal: both stand; applicability is unresolved; not a conflict and not a duplicate. If an execution is observed on the proposal, the report says "two approvals recorded" - it never names a denial that was not recorded.

## 11. Versioning and references

- This document is versioned with the workstream: **v0.7-draft**. Changes land through pull requests against [issue #41](https://github.com/aaif/wg-observability-and-traceability/issues/41); the review window follows the [working methods](../WORKING-METHODS.md) (specifications: at least 2 weeks). Revision 7 (2026-09-21) defines what establishes a denial as applicable - an exported reference from the execution to the decision it followed (R5), not the decision being the only one recorded - and requires the unresolved-applicability report to name only the decisions actually recorded; the single-denial fixture now establishes applicability explicitly, and a no-reference single-denial fixture is added. Revision 6 (2026-09-20) scopes the approval-inconsistency finding to an established applicable denial: with unresolved applicability the report is "execution observed; approval and denial recorded; applicable decision unresolved; enforcement unknown," an execution on a proposal with no recorded decision is reported as decision unknown rather than an inconsistency, and a three-record fixture carries the exact report wording. Revision 5 (2026-09-19) defines how multiple decisions on one proposal are read: all stand, applicability is unresolved, never selected by ordering or counting, and enforcement is unknown while unresolved; supersession via an explicit reference is recorded as open choice 11 under the Task 9 discipline, with two matching fixture cases. Revision 4 (2026-09-18) resolves the two boundary cases left open by revision 3: a present but unrecognized method is a mapping loss with no fallback to the mapping-file default, and one relationship exported through multiple methods is a single relationship with multiple observed methods rather than a conflict; matching fixture cases added. Revision 3 (2026-09-17) tightens §4 to require a link method per relationship record, with a permitted relaxation when the example's mapping file declares a uniform default; absence of both is treated as a mapping loss. Revision 2 (2026-09-16) applied reader-design feedback from [#45](https://github.com/aaif/wg-observability-and-traceability/issues/45): enforcement/evidence split in the approval rules, scoped identity namespaces for joins and deduplication, usage aggregation levels, one-to-many effects, pinned OTel source revisions, and new fixture cases for each.
- [Execution plan](https://github.com/aaif/wg-observability-and-traceability/pull/48) and its nine-task overview; task issues [#39](https://github.com/aaif/wg-observability-and-traceability/issues/39)–[#47](https://github.com/aaif/wg-observability-and-traceability/issues/47).
- [OTel GenAI semantic conventions: spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/be23fcc250f7/docs/gen-ai/gen-ai-spans.md) (pinned at `be23fcc250f7`) and [agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/b06f7a2c840c/docs/gen-ai/gen-ai-agent-spans.md) (pinned at `b06f7a2c840c`), including the [turn-entry discussion](https://github.com/open-telemetry/semantic-conventions-genai/issues/356).
- [AAIF Taxonomy & Landscape workstream](https://github.com/aaif/ws-taxonomy-landscape) and [taxonomy/trace-model crosswalk, issue #10](https://github.com/aaif/wg-observability-and-traceability/issues/10).
