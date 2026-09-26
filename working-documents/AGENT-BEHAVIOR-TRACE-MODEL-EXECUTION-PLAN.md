# Agent Behavior Trace Model: execution plan

Status: Living working group document - last reviewed 2026-09-01

This plan records the execution work following the [August 5](../meeting-minutes/2026-08-05.md) and [August 19](../meeting-minutes/2026-08-19.md) WG discussions. Initial scope is agreed; implementation is planned primarily for September. The nine task issues below are the plan of record. Their owners, status, and next steps are tracked in the issues.

## What we want to achieve

Make it possible to follow an agent's work across turns, interruptions, and system boundaries using OpenTelemetry.

The shared contract will describe **which relationships to record, how to identify the work they connect, and how different tools should interpret them**. It will use AAIF terminology and existing OTel conventions, adding guidance or proposing new conventions only where the examples show a need.

## What the first examples will prove

Start with four questions:

- **Continuity:** Which turns belong together, including after a pause or restart?
- **Calls and retries:** Which model calls served each turn, without counting the same work twice?
- **Approvals:** Which decision concerned an action, and did that action execute?
- **Effects:** Which external change can be connected to that execution?

Use a small support workflow: investigate a delayed order, propose creating a ticket, request approval, execute the action, and return to the conversation later. An independently instrumented test service records the ticket creation.

Implement it in **Goose and one independent agent or SDK**. Both must demonstrate the core session/turn behavior. Record unsupported capabilities rather than pretending every runtime behaves alike. These are initial examples for an extensible framework, not a limit on the agents or domains it should support.

## Tasks

Each issue contains the reason for the work, its scope, completion criteria, and dependencies. Implementation tasks also include concrete examples. Contributors can pick up a task or a piece of one; no single contributor is expected to deliver the whole plan.

| # | Task | Deliverable |
| --- | --- | --- |
| 1 | **[Document the execution plan](https://github.com/aaif/wg-observability-and-traceability/issues/39)** | Record the August direction and task breakdown. Done when the plan is merged. |
| 2 | **[Define the examples and capture the baseline](https://github.com/aaif/wg-observability-and-traceability/issues/40)** | Shared scenarios, expected results, and current telemetry from both implementations. Separate unsupported behavior from instrumentation or convention gaps. |
| 3 | **[Define the shared contract](https://github.com/aaif/wg-observability-and-traceability/issues/41)** | A short description of identities, turn boundaries, and relationships, mapped to AAIF terminology and OTel. Record unresolved definitions and review them with the relevant groups. |
| 4 | **[Build shared tests and a contribution template](https://github.com/aaif/wg-observability-and-traceability/issues/42)** | Sample records, expected answers, and checks that contributors can run. Allow focused gap examples without requiring a complete application. |
| 5 | **[Implement session and turn correlation](https://github.com/aaif/wg-observability-and-traceability/issues/43)** | Both examples connect completed turns and supported resumption across traces, without consumers querying private agent state. |
| 6 | **[Connect calls, approvals, and effects](https://github.com/aaif/wg-observability-and-traceability/issues/44)** | Tested relationships for provider calls/retries, approval decisions, tool execution, and independently observed changes. These are three assignable pieces within one task. |
| 7 | **[Check independent interpretation](https://github.com/aaif/wg-observability-and-traceability/issues/45)** | Two independently implemented readers or query paths produce the expected answers from both examples, including when records are missing, duplicated, delayed, or conflicting. |
| 8 | **[Make the examples easy to run and extend](https://github.com/aaif/wg-observability-and-traceability/issues/46)** | Runnable examples, mappings, coverage reports, and contributor instructions. Exercise two provider integrations across the agents and two standalone provider API examples. |
| 9 | **[Contribute the results upstream](https://github.com/aaif/wg-observability-and-traceability/issues/47)** | Focused instrumentation fixes, AAIF terminology proposals, and OTel GenAI guidance or semantic changes, each backed by a concrete example. |

Tasks 2 and 3 establish the baseline and contract. Tests and implementations then develop together. Upstream discussion starts during design; submissions follow the evidence. Each implementation task needs an owner and reviewer.

These tasks are the execution plan of record. The existing [trace-model recommendation issue #12](https://github.com/aaif/wg-observability-and-traceability/issues/12) and [PR #19](https://github.com/aaif/wg-observability-and-traceability/pull/19) remain separate recommendation work. The examples and findings here can inform that work without duplicating it.

## Boundaries to keep clear

- **AAIF vocabulary:** distinguish conversation continuity, runtime/protocol sessions, and an agent trajectory. Use published terms and aliases; label pending definitions and proposed terms such as "interaction turn." Each example maps its native labels to the same versioned contract. Coordinate the crosswalk through [issue #10](https://github.com/aaif/wg-observability-and-traceability/issues/10) and AAIF Taxonomy & Landscape.
- **Turn boundaries:** test one trace per turn as a candidate standalone default, not an existing universal OTel requirement. Preserve an existing caller trace. Define how to identify the turn-entry span and how approval waits and resumption affect a turn.
- **Evidence:** missing observations mean unknown, not zero or success. Observed approval is not proof of enforcement; a service-side receipt is not cryptographic attestation. Keep content capture opt-in.
- **Extensibility:** keep fixtures language-neutral and reuse existing OTel tooling. Do not require a new runtime or backend. Adding another agent should normally require a mapping and tests, not a redesign.

The September target is two agent examples, shared tests, contributor instructions, and evidence-backed upstream submissions. A single working example is useful progress, but does not establish cross-agent portability. Provider-only examples report their coverage separately from agent implementations.

General branching/delegation, context-compaction lineage, and correction mechanisms remain follow-on work. Open implementation choices include the second agent/SDK, initial provider pair, and contributor assignments. Task 3 resolves detailed relationship semantics as the examples develop; recording this plan does not make those semantics an adopted standard.

## References

- [Prior-work landscape survey](PRIOR-WORK.md) and [use cases](USE-CASES.md).
- [O&T taxonomy draft](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.kohq47xp41t5), [AAIF taxonomy working document](https://docs.google.com/document/d/1nn5dH89ao65hmRHjUD1rJUAd3rUIiIkrLLMkv-h-U3w/edit?tab=t.0), and [taxonomy workstream](https://github.com/aaif/ws-taxonomy-landscape).
- [WG trace-model proposal](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.y0c86cal5vr9) and [gap analysis](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.441hnuxp2967).
- [OTel GenAI conventions and reference tooling](https://github.com/open-telemetry/semantic-conventions-genai), including the [turn-entry discussion](https://github.com/open-telemetry/semantic-conventions-genai/issues/356).
