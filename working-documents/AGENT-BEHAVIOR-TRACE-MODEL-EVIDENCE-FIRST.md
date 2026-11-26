# Agent Behavior Trace Model: an evidence-first approach

*Proposal for the WG meeting, September 30, 2026*

Status: Working group proposal, agreed at the 2026-09-30 meeting. Converted from the WG working document.

## Why we're changing course

We looked at how the major coding agents and agent SDKs use OpenTelemetry today. They're far less consistent than their shared use of OTel GenAI conventions suggests:

- Of 27 coding agents, 19 export OpenTelemetry, but only 6 follow the GenAI span model closely.
- None emit the current usage metrics, and most still use outdated attribute names in various levels of consistency.
- They identify a session in at least seven different ways.
- None record tool approvals in a standard way, and several record a denied action as if it ran.

The agent SDKs show the same pattern. Of 34 SDKs and frameworks we checked (counting each language separately):

- None implement the current conventions.
- SDKs from the same vendor disagree with each other. Microsoft reports one service under four different provider names, and Agent Framework's Python and .NET versions record different things. Neither Anthropic's nor OpenAI's SDKs follow the provider page the conventions publish for them.
- The coding-agent problems repeat: several record a denied tool call as if it ran, and several count token usage more than once.

If implementations that claim the same standard disagree this much, we can't design a trace model from a specification or from what agents say they support. We have to start from what they actually emit, and proceed empirically.

In capturing a first baseline of Goose, AAIF's own agent, a pattern of behavior emerged:

- 0 of 91 model requests and 0 of 292 MCP requests carried trace context (part of the core OTel spec).
- Token usage was recorded three times per call, in different places.
- Approvals left no trace in its telemetry, and its CLI counted a denied tool call as a success.
- Background sub-agents started disconnected traces.

To be clear, this is not an indictment of Goose's implementation - but rather evidence that shows there is an endemic issue to being properly OTel compliant in a reliable way. When we began the reference implementation in September, we reached the same conclusion from the other direction. Building a full implementation of a spec is the wrong target. The more useful work is finding exactly where today's OpenTelemetry instrumentation falls short, and building to fix that.

## What we'll do

1. **Agree the scope.** Today: the four questions from the execution plan, and what milestone 1 does and doesn't cover.
2. **Gather evidence.** Capture what real agents emit for those questions, reproducibly. We start with Goose, AAIF's own open-source agent, which already has an OpenTelemetry integration (first baseline done), then add a second agent for comparison.
3. **Record the gaps.** Keep one shared list. Each gap links to the evidence that exposed it, and says whether the fix belongs in the agent's instrumentation or in OpenTelemetry.
4. **Contribute the fixes.** Instrumentation fixes go to the agents, starting with Goose. Convention changes go to the OpenTelemetry GenAI SIG, each backed by a runnable example.

OpenTelemetry stays the default. We don't write a competing specification, but instead we bring evidence to our OpenTelemetry partners.

## Likely proposals to OpenTelemetry

The survey already points to gaps that appear across nearly every agent, which makes them conventions problems rather than one agent's bug. Each will be confirmed with captured evidence before we propose it, and ordered in priority given the number/scope of impact of each issue across agents and SDK's. Where OpenTelemetry already has a discussion, we aim to join, unless the existing conversation has pivoted away from the core issue identified. We're focusing on places where implementations use the same thing to mean different things, or where nobody has agreed on a meaning yet.

| **Gap seen across agents** | **Evidence so far** | **Where it goes in OpenTelemetry** |
| --- | --- | --- |
| **Approvals aren't recorded in a standard way**, and denied actions often look like they ran | No agent uses a standard form; at least 5 of 19 record denied calls as tool executions | Existing work on tool-call decisions (semantic-conventions-genai #95, #535) |
| **No agreed marker for where a conversation or turn starts**, and no single session key | None of 19 mark it; at least seven different session attributes in use | Turn-entry discussion (#356) and agent-vs-workflow (#477) |
| **Sub-agents and background work can't be reliably linked** to the work that started them | 3 of 19 keep the child in the parent's trace; 1 uses links | Multi-agent (#243, #447) and background execution (#403, #445) |
| **Usage is counted at several levels**, and cost is reported under many names | At least 8 of 16 report nested totals; 7 different cost names | Billing details and cost (#503, #443) |
| **Retries aren't visible** as attempts of one logical call | 3 of 19 record an attempt number | No existing discussion yet; a candidate new issue |
| **The target of an external effect** (file, command, resource) isn't recorded apart from the full tool arguments | None of 19 | No existing discussion yet; a candidate new issue |

Some gaps are adoption of the full OTel spec, not convention work in OTel itself. For example, trace context propagation to MCP servers is already specified, but only 2 of 19 agents examined have implemented it. Those go to the agents as instrumentation fixes, starting with Goose as a reference implementation.

## What milestone 1 covers

| **Dimension** | **Covered** | **Deferred to milestone 2** |
| --- | --- | --- |
| Execution Structure | Sessions and turns, including resume; model calls and retries counted once | Delegation and lineage across agents |
| Reasoning & Planning | Only indirectly, through proposed actions and approvals | Capturing reasoning and planning |
| Outcomes & Effects | Approvals linked to the actions they gate; external effects | Whether the user's intent or goal was met |

Milestone 1 isn't complete coverage of the behavioral model. Each deferral gets its own tracked issue.

## Timeline

- **October:** share the Goose baseline, build the gap list, and produce a first-cut draft of the Gap Analysis and Trace Model Recommendation for WG review.
- **End of November:** publish after the charter's two-week review, within its one-month window.

## What we're asking of the WG today

1. Agree the milestone 1 scope and the four steps above.
2. Help choose the second agent/SDK for comparison.
3. Take part asynchronously, in Discord and GitHub, where most of this work will happen. Tell us which areas you want to contribute to.
