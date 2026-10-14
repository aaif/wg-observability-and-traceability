# Agent Behavior Trace Model: execution plan

Status: Living working group document - revision proposed at the September 30, 2026 WG meeting and updated for October 14, 2026; previous version reviewed 2026-09-01

This plan records the execution work following the [August 5](../meeting-minutes/2026-08-05.md) and [August 19](../meeting-minutes/2026-08-19.md) WG discussions. This revision puts evidence first. At the [September 30](https://github.com/aaif/wg-observability-and-traceability/blob/main/meeting-minutes/2026-09-30.md) meeting the WG agreed to focus the work on finding the semantic gaps in today's OpenTelemetry instrumentation, and on a conformance check that shows them. It replaces the nine parallel tasks of the previous version with four phases, where each phase starts from what the previous one found. Owners, status, and next steps are tracked in the issues.

## Why evidence first

We looked at how the major coding agents and agent SDKs use OpenTelemetry today. They are far less consistent than their shared use of the OTel GenAI conventions suggests. Of 27 coding agents, 19 export OpenTelemetry, but only 6 follow the GenAI span model closely. None emit the current usage metrics. Sessions are identified in at least seven different ways, and no agent records tool approvals in a standard form. The 28 agent SDKs and frameworks we checked show the same pattern: none are on the current conventions, and SDKs from the same vendor disagree with each other. AI gateways, which see every call from every client behind them, add their own gaps: none emits the current usage metrics, each reports cost under its own name, and none says whether it counts the client's request or each provider attempt. When implementations that claim the same standard disagree this much, the WG can't design a trace model from a specification or from what agents say they support. It has to start from what they actually emit.

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
- **More agents for comparison.** Since September 30, several more coding agents have been captured with the same scenarios. A gap seen in independent implementations is evidence of a shared need rather than one agent's bug. The WG chooses which of them to carry forward beside Goose.

Unsupported capabilities are recorded as such, rather than forced.

## Phases

| Phase | Work | Issues |
| --- | --- | --- |
| **1. Agree** | Agree the scope, questions, agents, and dimension coverage above | [#12](https://github.com/aaif/wg-observability-and-traceability/issues/12) (umbrella for the recommendation) and a new milestone 1 issue |
| **2. Evidence** | A reproducible capture kit; baselines for Goose and the comparison agents; a conformance check that scores a captured run against the four questions, which anyone can run on their own agent; a shared register of observed gaps, each linked to the evidence that exposed it | [#46](https://github.com/aaif/wg-observability-and-traceability/issues/46), [#40](https://github.com/aaif/wg-observability-and-traceability/issues/40), plus new issues for the comparison agents and the gap register |
| **3. Interpret** | Write down only what the evidence shows we need; test cases built from real captures; two independent readers on real captures | [#41](https://github.com/aaif/wg-observability-and-traceability/issues/41), [#42](https://github.com/aaif/wg-observability-and-traceability/issues/42), [#45](https://github.com/aaif/wg-observability-and-traceability/issues/45) |
| **4. Contribute** | Instrumentation fixes to the agents, starting with Goose; evidence-backed proposals to the OpenTelemetry GenAI SIG, each with a runnable example | [#43](https://github.com/aaif/wg-observability-and-traceability/issues/43), [#47](https://github.com/aaif/wg-observability-and-traceability/issues/47) |

Each gap in the register is classified as unsupported behavior, an agent instrumentation gap, an OpenTelemetry guidance gap, or a missing convention. Phases 3 and 4 start from the register; nothing is specified ahead of the evidence. The issues will be updated to match this plan once it is agreed.

## Likely proposals to OpenTelemetry

We won't propose renames. Old attribute names get updated over time as the conventions settle. We'll focus on places where implementations use the same thing to mean different things, or where nobody has agreed on a meaning yet.

Each gap below shows up in nearly every agent we looked at, so it's a conventions question and not one agent's bug. We'll confirm each one with captured evidence before proposing anything, and we'll start with the gaps that affect the most agents and SDKs. If OpenTelemetry already has a discussion open, we'll join it, unless it has drifted away from the problem.

| Gap | Where it goes |
| --- | --- |
| Approvals aren't recorded in a standard way, and denied actions often look like they ran | Ongoing conversations: [tool-call decisions](https://github.com/open-telemetry/semantic-conventions-genai/issues/95), [a proposed decision record](https://github.com/open-telemetry/semantic-conventions-genai/pull/535) |
| Nothing marks where a conversation or turn starts, and the session key means different things in different agents (`gen_ai.conversation.id` alone is used with five meanings) | Ongoing conversations: [marking the start of a turn](https://github.com/open-telemetry/semantic-conventions-genai/issues/356), [agent versus workflow](https://github.com/open-telemetry/semantic-conventions-genai/issues/477) |
| Sub-agents and background work can't be reliably linked to the work that started them | Ongoing conversations: [multi-agent tracing](https://github.com/open-telemetry/semantic-conventions-genai/issues/243), [a proposed multi-agent model](https://github.com/open-telemetry/semantic-conventions-genai/pull/447), [background execution](https://github.com/open-telemetry/semantic-conventions-genai/issues/403), [a proposed background model](https://github.com/open-telemetry/semantic-conventions-genai/pull/445) |
| Token usage is repeated at several levels, so adding it up counts it twice or more | Ongoing conversation: [aggregated token usage](https://github.com/open-telemetry/semantic-conventions-genai/issues/19) |
| Retries can't be told apart from new calls | Ongoing conversation: [counting operations or attempts](https://github.com/open-telemetry/semantic-conventions-genai/issues/476), closed with an invitation to reopen given evidence |
| Cost has no standard name, every gateway figure is an estimate from its own price table, and estimated token counts are not marked | Ongoing conversations: [billing details](https://github.com/open-telemetry/semantic-conventions-genai/issues/503), [a proposed cost attribute](https://github.com/open-telemetry/semantic-conventions-genai/pull/443) |
| A gateway is both a server to its clients and a client of the provider, and the conventions define neither role for it | No discussion yet, so this would be a new issue |
| The thing an action changed (a file, a command, a resource) is only recorded inside the full tool arguments | No discussion yet, so this would be a new issue |

Some gaps are about adoption, not the conventions. For example, the conventions already say how to pass trace context to MCP servers, but few agents do it. Those fixes go to the agents themselves, starting with Goose as the reference implementation. The WG won't propose them to OpenTelemetry.

## Boundaries to keep clear

- **AAIF vocabulary:** distinguish conversation continuity, runtime/protocol sessions, and an agent trajectory. Use published terms and aliases; label pending definitions and proposed terms such as "interaction turn." Each example maps its native labels to the same versioned contract. Coordinate the crosswalk with AAIF Taxonomy & Landscape.
- **Turn boundaries:** test one trace per turn as a candidate standalone default, not an existing universal OTel requirement. Preserve an existing caller trace. Define how to identify the turn-entry span and how approval waits and resumption affect a turn.
- **Evidence:** missing observations mean unknown, not zero or success. Observed approval is not proof of enforcement; a service-side receipt is not cryptographic attestation. Keep content capture opt-in.
- **Extensibility:** keep fixtures language-neutral and reuse existing OTel tooling. Do not require a new runtime or backend. Adding another agent should normally require a mapping and tests, not a redesign.
- **Contributions:** proposals are evaluated against the evidence, whatever their source, and substantial proposals are introduced on a WG call.

## Timeline

- **October 14:** the main gaps so far, with examples from Goose and the other captured agents, SDKs, and gateways.
- **October 28:** the gap register and a first-cut draft of the Gap Analysis and Trace Model Recommendation for WG review.
- **End of November:** publication after the charter's two-week review, within its one-month timeliness window.

Success for the first cut is a direction the WG agrees to take forward in discussion with our OpenTelemetry partners.

## References

- [Prior-work landscape survey](PRIOR-WORK.md) and [use cases](USE-CASES.md).
- [O&T taxonomy draft](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.kohq47xp41t5), [AAIF taxonomy working document](https://docs.google.com/document/d/1nn5dH89ao65hmRHjUD1rJUAd3rUIiIkrLLMkv-h-U3w/edit?tab=t.0), and [taxonomy workstream](https://github.com/aaif/ws-taxonomy-landscape).
- [WG trace-model proposal](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.y0c86cal5vr9) and [gap analysis](https://docs.google.com/document/d/1CyUJK1tK_XtJegRBXaTK9t_cntYgE9zfteMZyKvfKGQ/edit?tab=t.441hnuxp2967).
- [OTel GenAI conventions and reference tooling](https://github.com/open-telemetry/semantic-conventions-genai).
