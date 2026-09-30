# Agent Behavior Trace Model: execution plan

Status: Living working group document - revision proposed for the September 30, 2026 WG meeting; previous version reviewed 2026-09-01

This plan records the execution work following the [August 5](../meeting-minutes/2026-08-05.md) and [August 19](../meeting-minutes/2026-08-19.md) WG discussions. This revision puts evidence first. It replaces the nine parallel tasks of the previous version with four phases, where each phase starts from what the previous one found. Owners, status, and next steps are tracked in the issues.

## Why evidence first

We looked at how the major coding agents and agent SDKs use OpenTelemetry today. They are far less consistent than their shared use of the OTel GenAI conventions suggests. Of 27 coding agents, 19 export OpenTelemetry, but only 6 follow the GenAI span model closely. None emit the current usage metrics. Sessions are identified in at least seven different ways, and no agent records tool approvals in a standard form. The 28 agent SDKs and frameworks we checked show the same pattern: none are on the current conventions, and SDKs from the same vendor disagree with each other. When implementations that claim the same standard disagree this much, the WG can't design a trace model from a specification or from what agents say they support. It has to start from what they actually emit.

Starting the September reference implementation led to the same conclusion. The more useful work is not a full implementation of a new specification, but finding exactly where today's OpenTelemetry instrumentation falls short, and building to fix that.

## What we want to achieve

Make it possible to follow an agent's work across turns, interruptions, and system boundaries using OpenTelemetry.

The shared contract will describe **which relationships to record, how to identify the work they connect, and how different tools should interpret them**. It will use AAIF terminology and existing OTel conventions, adding guidance or proposing new conventions only where the evidence shows a need. OpenTelemetry stays the default: the WG brings evidence to the OpenTelemetry GenAI SIG rather than writing a competing specification.

## The four questions

- **Continuity:** Which turns belong together, including after a pause or restart?
- **Calls and retries:** Which model calls served each turn, without counting the same work twice?
- **Approvals:** Which decision concerned an action, and did that action execute?
- **Effects:** Which external change can be connected to that execution?

The scenario is a small support workflow: investigate a delayed order, propose creating a ticket, request approval, execute the action, and return to the conversation later. An independently instrumented test service records the ticket creation.

## Dimension coverage

Milestone 1 does not cover the whole behavioral model. Following review of the previous version ([#48](https://github.com/aaif/wg-observability-and-traceability/pull/48)), this table states what each of the charter's three dimensions directly models, enables, or defers.

| Dimension | Models directly | Enables | Defers to milestone 2 |
| --- | --- | --- | --- |
| Execution Structure | Session and turn continuity, including resume; model calls and retries counted once; tool execution linked to the call that requested it | Recording sub-agent placement where a runtime supports it | Delegation and lineage across agents |
| Reasoning & Planning | Only indirectly, through proposed actions and the approvals that gate them | Recording whether reasoning occurred, and whether it was captured directly or reconstructed | Reasoning and planning capture, with the State, Context & Reasoning focus group |
| Outcomes & Effects | Approvals linked to the action they gate, including denials with no execution; external effects linked to the execution that caused them | Distinguishing observed from declared outcomes | Whether the user's intent or goal was met |

## Agents

- **Goose**, AAIF's own open-source agent, is the reference implementation. It already has an OpenTelemetry integration, so the work is to capture what it emits, find the gaps, and fix them. The Goose capture is shared with the ARD lifecycle work ([#49](https://github.com/aaif/wg-observability-and-traceability/issues/49)).
- **A second agent or SDK**, chosen by the WG, for comparison. A gap seen in two independent implementations is evidence of a shared need rather than one agent's bug.

Unsupported capabilities are recorded as such, rather than forced.

## Phases

| Phase | Work | Issues |
| --- | --- | --- |
| **1. Agree** | Agree the scope, questions, agents, and dimension coverage above | [#12](https://github.com/aaif/wg-observability-and-traceability/issues/12) (umbrella for the recommendation) and a new milestone 1 issue |
| **2. Evidence** | A reproducible capture kit; baselines for Goose and the second agent; a shared register of observed gaps, each linked to the evidence that exposed it | [#46](https://github.com/aaif/wg-observability-and-traceability/issues/46), [#40](https://github.com/aaif/wg-observability-and-traceability/issues/40), plus new issues for the second agent and the gap register |
| **3. Interpret** | Write down only what the evidence shows we need; test cases built from real captures; two independent readers on real captures | [#41](https://github.com/aaif/wg-observability-and-traceability/issues/41), [#42](https://github.com/aaif/wg-observability-and-traceability/issues/42), [#45](https://github.com/aaif/wg-observability-and-traceability/issues/45) |
| **4. Contribute** | Instrumentation fixes to the agents, starting with Goose; evidence-backed proposals to the OpenTelemetry GenAI SIG, each with a runnable example | [#43](https://github.com/aaif/wg-observability-and-traceability/issues/43), [#47](https://github.com/aaif/wg-observability-and-traceability/issues/47) |

Each gap in the register is classified as unsupported behavior, an agent instrumentation gap, an OpenTelemetry guidance gap, or a missing convention. Phases 3 and 4 start from the register; nothing is specified ahead of the evidence. The issues will be updated to match this plan once it is agreed.

## Likely proposals to OpenTelemetry

These gaps appear across nearly every agent we surveyed, which makes them conventions questions rather than individual bugs. Each will be confirmed with captured evidence before it is proposed, and they are prioritized by how many agents and SDKs each affects and how broadly. Where OpenTelemetry already has a discussion, the WG joins it, unless that discussion has moved away from the core issue.

| Gap | Where it goes |
| --- | --- |
| Approvals aren't recorded in a standard way, and denied actions often look like they ran | [semantic-conventions-genai #95](https://github.com/open-telemetry/semantic-conventions-genai/issues/95), [#535](https://github.com/open-telemetry/semantic-conventions-genai/pull/535) |
| No agreed marker for where a conversation or turn starts, and no single session key | [#356](https://github.com/open-telemetry/semantic-conventions-genai/issues/356), [#477](https://github.com/open-telemetry/semantic-conventions-genai/issues/477) |
| Sub-agents and background work can't be reliably linked to the work that started them | [#243](https://github.com/open-telemetry/semantic-conventions-genai/issues/243), [#447](https://github.com/open-telemetry/semantic-conventions-genai/pull/447), [#403](https://github.com/open-telemetry/semantic-conventions-genai/issues/403), [#445](https://github.com/open-telemetry/semantic-conventions-genai/pull/445) |
| Usage is counted at several levels, and cost is reported under many names | [#19](https://github.com/open-telemetry/semantic-conventions-genai/issues/19) for usage; [#503](https://github.com/open-telemetry/semantic-conventions-genai/issues/503), [#443](https://github.com/open-telemetry/semantic-conventions-genai/pull/443) for cost |
| Retries aren't visible as attempts of one logical call | [#476](https://github.com/open-telemetry/semantic-conventions-genai/issues/476), closed with an invitation to reopen given evidence |
| The target of an external effect isn't recorded apart from the full tool arguments | No existing discussion; candidate new issue |

Some gaps are adoption rather than conventions. For example, trace context propagation to MCP servers is already specified, but few agents do it. Those go to the agents as instrumentation fixes.

## Boundaries to keep clear

- **AAIF vocabulary:** distinguish conversation continuity, runtime/protocol sessions, and an agent trajectory. Use published terms and aliases; label pending definitions and proposed terms such as "interaction turn." Each example maps its native labels to the same versioned contract. Coordinate the crosswalk with AAIF Taxonomy & Landscape.
- **Turn boundaries:** test one trace per turn as a candidate standalone default, not an existing universal OTel requirement. Preserve an existing caller trace. Define how to identify the turn-entry span and how approval waits and resumption affect a turn.
- **Evidence:** missing observations mean unknown, not zero or success. Observed approval is not proof of enforcement; a service-side receipt is not cryptographic attestation. Keep content capture opt-in.
- **Extensibility:** keep fixtures language-neutral and reuse existing OTel tooling. Do not require a new runtime or backend. Adding another agent should normally require a mapping and tests, not a redesign.
- **Contributions:** proposals are evaluated against the evidence, whatever their source, and substantial proposals are introduced on a WG call.

## Timeline

- **October:** Goose baseline, the gap register, and a first-cut draft of the Gap Analysis and Trace Model Recommendation for WG review.
- **End of November:** publication after the charter's two-week review, within its one-month timeliness window.

Success for the first cut is a direction the WG agrees to take forward in discussion with our OpenTelemetry partners.

## References

- [Prior-work landscape survey](PRIOR-WORK.md) and [use cases](USE-CASES.md).
- [O&T taxonomy draft](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.kohq47xp41t5), [AAIF taxonomy working document](https://docs.google.com/document/d/1nn5dH89ao65hmRHjUD1rJUAd3rUIiIkrLLMkv-h-U3w/edit?tab=t.0), and [taxonomy workstream](https://github.com/aaif/ws-taxonomy-landscape).
- [WG trace-model proposal](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.y0c86cal5vr9) and [gap analysis](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.441hnuxp2967).
- [OTel GenAI conventions and reference tooling](https://github.com/open-telemetry/semantic-conventions-genai).
- Survey of OpenTelemetry support in coding agents and agent SDKs: link to follow.
