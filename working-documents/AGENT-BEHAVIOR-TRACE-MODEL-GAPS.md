# Agent Behavior Trace Model: main gaps found

*Update for the WG meeting, October 14, 2026.*

Status: Working group update, reviewed at the 2026-10-14 meeting. Converted from the WG working document.

On September 30, the WG agreed to an evidence-first approach ([Agent Behavior Trace Model: an evidence-first approach](AGENT-BEHAVIOR-TRACE-MODEL-EVIDENCE-FIRST.md)). Since then, AI gateways were added to the coding agents and SDKs in scope. Several coding agents, Goose included, were also run against a scripted stand-in model, and their telemetry output was examined.

All examples in this document come from coding agents, agent SDKs, or AI gateways that offer OpenTelemetry support. All of these projects state that they follow the OpenTelemetry GenAI conventions. The conventions are still in Development status, so differences between projects are expected. The examples are public behavior and can be checked.

## 1. A denied action is recorded as if it ran

When a user or a policy blocks a tool call, the telemetry often shows a tool execution.

- Goose: approvals and denials are sent only in editor protocol messages, not in telemetry. A denied call leaves no record. The CLI tool counter records the denied call as a success.
- AG2: a denied call is recorded as a successful tool span. The span result is the text of the denial.
- OpenAI Agents SDK: each rejection is labeled "manually rejected by user", also when a rule rejected the call.
- Azure AI Foundry: the approve or deny value is recorded only when message content capture is on. With default settings, a trace does not show whether an approval was given.

No standard record exists for who decided, what the decision was, and whether the action ran. Ongoing conversations: [tool-call decisions](https://github.com/open-telemetry/semantic-conventions-genai/issues/95) and [a proposed decision record](https://github.com/open-telemetry/semantic-conventions-genai/pull/535).

## 2. The start of a conversation is not marked, and "session" has different meanings

No marker shows where a conversation or a turn starts. Each project selects its own session key. The standard key, `gen_ai.conversation.id`, is also used with different meanings.

- CrewAI: the key is set to the task ID. One run shows as several conversations.
- Koog: the key is set to the run ID. Each run shows as a new conversation.
- Mastra: the key is the memory thread.
- Pydantic AI: the key is a conversation that continues across runs.
- VS Code: the resource attribute `session.id` identifies one editor window, not one chat.
- LangSmith: in exported data, `langsmith.trace.session_id` identifies a project, not a conversation.
- Coding agents: a resumed conversation starts a new trace. The new trace is connected to the old trace only by an attribute.

Grouping by session gives different results, based on how each project does the grouping. Ongoing conversations: [marking the start of a turn](https://github.com/open-telemetry/semantic-conventions-genai/issues/356) and [agent versus workflow](https://github.com/open-telemetry/semantic-conventions-genai/issues/477).

## 3. Sub-agents and background work are not connected to their origin

When work is given to a sub-agent or run in the background, the link to the originating turn is usually lost.

- Goose: a background sub-agent starts a separate trace. The trace has no link to its parent.
- Strands: background tool runs start with no parent.
- Mastra: links are recorded internally, but are removed at export.
- Pydantic AI and Google ADK: a delegated agent gets a new conversation ID.
- OpenTelemetry bridge for the OpenAI Agents SDK: handoff spans are removed, because the conventions do not define them.

As a result, the cost and the effects of delegated work cannot be connected to the request that caused them. Ongoing conversations: [multi-agent tracing](https://github.com/open-telemetry/semantic-conventions-genai/issues/243), [a proposed multi-agent model](https://github.com/open-telemetry/semantic-conventions-genai/pull/447), [background execution](https://github.com/open-telemetry/semantic-conventions-genai/issues/403) and [a proposed background model](https://github.com/open-telemetry/semantic-conventions-genai/pull/445).

## 4. Token usage is counted two or three times

The same token counts are often put on several nested spans: the call, the step, and the full run. No attribute identifies the correct total. A sum of the spans gives a count that is too high.

- Goose: usage is recorded at three levels. In most runs, the sum of the spans was exactly three times the real usage.
- Copilot CLI: the product documentation warns that a sum of its spans counts usage two times.
- AG2: the project design notes state that each direct model call is recorded two times.
- Mastra: usage was moved to one span for each call. The reason given: nested usage "doubled Langfuse trace cost and tripled Phoenix token totals".
- Haystack: token counts are exported only with the prompt. When prompt capture is off, token counts are also removed.

Ongoing conversation: [aggregated token usage](https://github.com/open-telemetry/semantic-conventions-genai/issues/19).

## 5. Retries are not visible

When a model call fails and is tried again, most telemetry does not show that two attempts served one logical call.

- Goose: a rate-limit retry occurs inside one span. The span has no attempt count and no error. Only a warning log shows the retry.
- Vercel AI SDK: in a streaming call, a retry removes the spans of the failed attempt.
- LangGraph: the attempt number is known, but is not exported.
- Gateways: retries and fallbacks to other providers are frequent, and each gateway shows them differently. Envoy AI Gateway has one span for each client request, but records metrics for each provider attempt. In LiteLLM, all attempts share one ID, and no attribute identifies each attempt.

When attempts are not recorded, input tokens used by a failed attempt are lost from the count. Ongoing conversation: [counting operations or attempts](https://github.com/open-telemetry/semantic-conventions-genai/issues/476). This issue was closed in September, with an invitation to reopen it if a real example is supplied. The Goose capture is one example.

## 6. Cost has no standard name, estimates are not marked, and input tokens are defined differently

No convention for cost exists. Each project that reports cost uses its own name. Most projects do not identify the source of the value.

- Gateways report cost as `gen_ai.usage.cost`, `gen_ai.usage.total_cost`, `kong.gen_ai.llm.cost`, `vercel.ai_gateway.cost.total`, and other names. Several gateways put their own name in the `gen_ai.*` namespace, where it looks like a standard attribute.
- Each gateway cost value is an estimate from the price table of that gateway. No value is the provider bill, and almost no gateway identifies the value as an estimate.
- Bifrost: a cost of zero is recorded when a model cannot be priced. An unknown cost then looks like a free call.
- Token counts can also be estimates. LiteLLM uses a local tokenizer when a stream ends without usage data. The estimated count is not marked. Only OpenRouter marks estimated counts.

The value of `gen_ai.usage.input_tokens` is also different between projects. The conventions state that this value includes cached input tokens. The cached part is also reported separately, in `gen_ai.usage.cache_read.input_tokens`.

The providers use different rules. The OpenAI API includes cached tokens in its input count. The Anthropic API does not include them. Each project selects one rule. Few projects state which rule they use.

- LiteLLM, Bifrost, agentgateway, and Traefik Hub include cached tokens in `gen_ai.usage.input_tokens`. This agrees with the conventions.
- Envoy AI Gateway: the metric includes cached tokens for Anthropic and Bedrock. The span on the Anthropic route does not include them. Thus one gateway reports two different values.
- Plano: cached tokens are included for OpenAI-style responses. Cached tokens are not included for Anthropic-style responses.
- Azure: `ActiveTokens` is documented as total tokens minus cached tokens.
- Cloudflare, Databricks, Amazon Bedrock, Vercel, and Kong do not state if cached tokens are included.

Thus a sum of `gen_ai.usage.input_tokens` across projects or providers adds two different quantities.

Ongoing conversations: [billing details](https://github.com/open-telemetry/semantic-conventions-genai/issues/503) and [a proposed cost attribute](https://github.com/open-telemetry/semantic-conventions-genai/pull/443).

## 7. The role of a gateway is not defined in the conventions

The conventions define a client that calls a model, and a model server. A gateway is both: it serves the client request, and it calls the provider.

- Envoy AI Gateway, Kong, Traefik Hub, and Tyk AI Studio emit the client token metric and the server duration metric from the same component.
- The span for a model call is CLIENT in some gateways, SERVER in others, and INTERNAL in others.
- No rule states whether a gateway counts the client request or each provider attempt. A count of calls therefore gives a different result in each gateway.

No ongoing conversation was found. A new issue is proposed.

## Proposed next steps

1. Keep one shared list of these gaps in the WG repository. Each entry includes its examples, and states whether the fix belongs in a project or in OpenTelemetry.
   - This will be PR'd after the WG review today as separate PR's per gap identified.
2. Add these examples to the ongoing conversations. Start with the gaps that affect the most projects: denied actions (1), usage counted more than once (4), and the start of a conversation (2).
3. Supply a first draft of the gap analysis for review at the next meeting, and send the proposals for the first 3 to The OTel GenAI SIG. This gap analysis will be a full report of behaviors on these semantic conventions for coding agents, agent SDK's, and gateways.
4. Regardless of the outcome of the acceptance of these upstream proposals, the AAIF WG will publish an independent evidence-based recommendation and library of runnable checks to validate conformance and reportability.

## Requests to the WG

1. Review the revised execution plan (PR #60).
2. Identify the gaps that are most important, and any gaps that are missing - beyond what are mentioned here in this document.
3. Volunteer for a gap, or identify people in the OpenTelemetry GenAI SIG who already work on one.
