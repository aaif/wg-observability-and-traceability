# Agent → Tool Boundary Deep-Dive: Local CLI Realization

**Status:** First filled matrix pass, ready for WG review

**Last updated:** 2026-09-03

**Owner:** [@fangxiu-wf](https://github.com/fangxiu-wf), following the invitation in [issue #29](https://github.com/aaif/wg-observability-and-traceability/issues/29#issuecomment-5410557135)

**Inputs:** [cross-boundary observability model (PR #25)](https://github.com/aaif/wg-observability-and-traceability/pull/25), [PRIOR-WORK.md](./PRIOR-WORK.md), W3C and OpenTelemetry specifications, and the merged [LoongSuite Pilot implementation (PR #316)](https://github.com/alibaba/loongsuite-pilot/pull/316)

## 1. Purpose

This document delivers a first filled matrix pass for the direct **Agent → Tool** boundary requested in [issue #29](https://github.com/aaif/wg-observability-and-traceability/issues/29). It uses a local CLI subprocess as one concrete realization and provides a worked implementation note based on LoongSuite Pilot.

The boundary is first-class because an agent can invoke a tool directly without a Skill intermediary. A common example is a coding agent invoking a shell command that launches a user-owned CLI process. The agent runtime owns the tool decision and process launch, while the child process may be independently instrumented and owned by a different party.

The canonical matrix boundary in this document is the semantic **Agent → Tool** relationship. The local CLI case also crosses an operational **Agent Runtime → Local Process** boundary. They are related but not interchangeable: the former describes the agent-level decision and tool invocation, while the latter describes the process-launch mechanism that realizes it.

The purpose is not to standardize a product-specific carrier. It is to identify:

- which field semantics and carrier mechanics are already standardized;
- where agent runtimes still break or obscure propagation;
- what must happen before process start to preserve the causal relationship;
- how to validate the boundary against the process that actually ran; and
- which remaining gaps should be coordinated with existing standards efforts.

## 2. Boundary description

The reference shape is:

```text
optional upstream caller
  └── agent turn / invocation
      └── tool execution span              ← Agent → Tool semantic boundary
          └── [optional CLI caller span]
              └── local CLI execution span ← Agent Runtime → Local Process boundary
                  └── CLI sub-operations and downstream calls
```

The boundary has two related surfaces:

1. **Agent execution surface:** the model or agent selects a tool, produces a tool call identifier and arguments, and the runtime authorizes and schedules the call.
2. **Operating-system process surface:** the runtime resolves a command, constructs a child environment and arguments, starts a process, observes its exit, and returns a result to the agent.

The matrix below is therefore an Agent → Tool row. Executable and process fields are concrete observations contributed by the local CLI realization; they do not redefine the canonical boundary as a process-only boundary.

For a local subprocess there may be no network protocol or request headers. Context therefore has to cross during process creation. If the agent runtime learns about the tool call only from a transcript after the child exits, it is too late for the child process to use the eventual tool span as its parent.

This boundary covers directly launched, finite CLI processes. Long-running daemons, MCP servers, remote APIs, container schedulers, and Agent → Agent delegation have overlapping but distinct lifecycle and transport requirements.

## 3. Filled matrix pass

| Field | What should be observable | Coverage today | Open gap |
| :-- | :-- | :-- | :-- |
| Identity | Agent, principal, session/turn, tool name and call ID; resolved executable name/path/version; child process ID; telemetry service/resource identity | OpenTelemetry GenAI defines agent and tool identity including `gen_ai.tool.name` and `gen_ai.tool.call.id`; OpenTelemetry CLI conventions define executable name/path and PID | No common cross-runtime identity binds the agent tool call, the exact executable artifact that ran, and the principal on whose behalf it ran; executable digest and version are not consistently available |
| Context | Active trace context; optional invocation-scoped baggage; sanitized tool arguments, working directory, constraints, policy and budget | W3C Trace Context and Baggage define propagation fields; the OpenTelemetry environment-variable carrier specification defines normalized environment carriers for process boundaries | Agent runtimes may filter or reconstruct child environments; adoption of the environment carrier specification is uneven; turn/task identity, deadline, budget and policy context have no common local-CLI profile |
| Relationship | Governing agent/turn → tool call → actual child execution; an in-lifetime synchronous CLI span is a child of the observable span that owns process launch, while the causal path remains under the tool execution; retries and siblings retain distinct identity; detached/background execution uses a relationship appropriate to its lifecycle | W3C Trace Context provides parent/child causality; OpenTelemetry GenAI models `execute_tool`; CLI conventions define caller and callee execution spans | Late transcript-only instrumentation cannot provide stable child-visible causal context; guidance is missing on whether `execute_tool` owns process launch directly or contains a separate CLI caller span; a Span Link may represent detached/background work more accurately when a simple parent/child tree would misstate ownership or lifecycle |
| Lifecycle | selected → authorized/denied → context prepared → spawn requested → process started → running → exited/errored/timed out/canceled; retry/fallback/compensation recorded | GenAI tool spans and CLI caller/callee spans represent duration and error status; process exit code covers the normal finite-process outcome | No shared lifecycle joins agent hooks, process-spawn failures, OS execution and later transcript reconciliation; queue time, approval time, cancellation and background completion are inconsistently represented |
| Outcome | Structured or unstructured result, process exit code, error type, partial output references, timeout/cancel status and externally visible side effects | GenAI tool-call result is opt-in; CLI conventions define `process.exit.code` and `error.type` | A successful exit does not describe files, APIs or resources changed; side-effect manifests, partial results and compensation outcomes are not standardized; stdout/stderr and arguments may contain sensitive data |
| Provenance | Tool definition and command source; runtime/plugin/skill that produced the call; executable path/version/digest; instrumentation version; observer and evidence class | GenAI records tool name/type/description; CLI conventions expose executable path; OpenTelemetry Resource and instrumentation-scope metadata identify telemetry producers | Declared tool schema can diverge from the resolved command and executable; shell expansion and wrappers obscure what ran; observer attribution and artifact digest are not consistently carried across the boundary |
| Security | Authorization/approval decision; permission and credential scope; sandbox, cwd and egress policy; child-environment allowlist; redaction policy; trust level of the child | W3C specifications include privacy/security constraints; the OpenTelemetry environment carrier warns against sensitive values; CLI arguments are not recommended by default without sanitization | Agent policy decisions lack a portable observation model; context can be stripped, overwritten or leaked to an untrusted child; there is no common record of declared versus observed permissions or granted versus used scope |
| Timing | Selection, approval, pre-execution preparation, spawn request, process start, first output and end; queue, execution, retry and cancellation durations | Tool and CLI spans provide start/end duration; OpenTelemetry conventions cover timeout/error classification | The hook, transcript and OS may use different clocks and observation points; pre-execution and spawn latency are rarely separated; background-process timing and late result collection remain ambiguous |

### 3.1 Candidate row for the seed matrix

| Boundary | Identity | Context | Relationship | Lifecycle | Outcome | Provenance | Security | Timing |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Agent → Tool (local CLI realization) | Agent/principal/session/turn; tool name and call ID; executable identity and child PID | Trace Context; optional Baggage; sanitized arguments and constraints | Agent/turn → tool call → child process; synchronous child spans use the documented process-launch span as parent while remaining under tool execution; detached/background work may use Span Links; retries and siblings retain distinct identity | selected → authorized → context-prepared → spawn-requested → started → running → exited/errored/timed-out/canceled | Result, exit/status code, partial output, error and externally visible side effects | Tool/command source; executable path/version/digest; instrumentation and observer identity | Approval and permission scope; sandbox/egress policy; environment allowlist; credential reference; redaction | Selection, approval, preparation, spawn, start, first-output and end timestamps; queue/execution/retry/cancel duration |

## 4. Standards coverage and the remaining portability gap

### 4.1 Tool and process spans

The [OpenTelemetry GenAI execute-tool convention](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md#execute-tool-span) is in Development status. It defines an `execute_tool` operation, an INTERNAL span, and attributes for tool name, call ID, type, arguments, result and error. Arguments and results are opt-in because they may contain sensitive content.

The [OpenTelemetry CLI span conventions](https://opentelemetry.io/docs/specs/semconv/cli/cli-spans/) are also in Development status. They define caller and callee views of finite CLI process execution with executable identity, PID, exit code, error type and optionally sanitized arguments.

These conventions cover both sides semantically, but do not yet provide a worked Agent → Tool composition profile for a local CLI realization. In particular, implementations need guidance on:

- how the GenAI tool span composes with or suppresses a CLI caller span;
- what stable causal context must be available before the child starts, including when the observable tool span is materialized later;
- how a callee span relates to a tool call observed later from a transcript; and
- how retries, shell wrappers and background processes affect the relationship.

For a synchronous finite child whose execution is owned by the tool call, parent/child causality is the simplest model. For detached or background work whose ownership or lifetime is not nested cleanly under the tool call, a Span Link may be more accurate. Implementations should state which model they use and why.

### 4.2 Trace Context and environment-variable carriers

[W3C Trace Context](https://www.w3.org/TR/trace-context/) standardizes the `traceparent` and `tracestate` propagation fields. Its primary processing model is HTTP, with other protocols covered through extensions and protocol-specific integrations.

OpenTelemetry now has a [Release Candidate specification for environment variables as context propagation carriers](https://opentelemetry.io/docs/specs/otel/context/env-carriers/). It applies `TextMapPropagator` semantics to process environments, normalizes field names for environment-variable rules, and includes child-process operational guidance. For W3C propagators, the normalized keys are `TRACEPARENT`, `TRACESTATE` and `BAGGAGE`.

This materially narrows the gap originally described in issue #29: the local-process carrier is no longer wholly unspecified. The remaining gap is primarily **adoption and boundary enforcement**:

- agent runtimes do not consistently provide a lifecycle integration point for preparing per-child context before launch;
- runtimes may filter or reconstruct the environment after the agent process receives it;
- application code is still responsible for providing the per-child environment to the process-spawn mechanism;
- language SDK support and initialization-time extraction are not uniform; and
- conformance must verify the environment and spans observed by the actual child process, not only the agent-side declaration.

### 4.3 Trace Context, Baggage and Resource are different data planes

| Data plane | Standard role | Local-process representation | Boundary rule |
| :-- | :-- | :-- | :-- |
| Trace Context | Trace causality and vendor trace state | `TRACEPARENT`, `TRACESTATE` through the OpenTelemetry environment carrier | Use only for trace correlation; do not place business or identity data in these fields |
| Baggage | Application-defined, invocation-scoped properties associated with a distributed request or workflow | `BAGGAGE` through the environment carrier when a W3C Baggage propagator is enabled | Propagate only allowlisted, non-sensitive entries and only when downstream use is intentional |
| Resource attributes | Properties of the process/service/entity producing telemetry | `OTEL_RESOURCE_ATTRIBUTES`, consumed by the child SDK during Resource construction | Use for stable child-process/service identity and deployment metadata, not request-scoped propagation |
| Tool content | Tool identity, arguments, result and error | GenAI span attributes/events, subject to capture policy | Arguments/results are potentially sensitive and should remain opt-in and sanitized |

The [OpenTelemetry Baggage API](https://opentelemetry.io/docs/specs/otel/baggage/api/) treats Baggage as application-defined properties associated with a distributed request or workflow. The [Resource SDK specification](https://opentelemetry.io/docs/specs/otel/resource/sdk/#specifying-resource-information-via-an-environment-variable) requires SDKs to read `OTEL_RESOURCE_ATTRIBUTES` during Resource construction. These mechanisms should not be treated as interchangeable custom-attribute channels. Resource bootstrap is a parallel process-initialization concern and is intentionally excluded from the compact matrix's invocation Context cell.

## 5. Worked implementation: LoongSuite Pilot and Claude Code

The reference implementation was merged in [LoongSuite Pilot PR #316](https://github.com/alibaba/loongsuite-pilot/pull/316) on 2026-08-25. It instruments this path:

```text
optional upstream application
  └── Claude Code main-agent turn
      └── Bash TOOL span
          └── user-owned CLI instrumented with OpenTelemetry
```

### 5.1 Validated implementation pattern: pre-execution reservation and propagation

Pre-execution span-ID reservation is one validated implementation pattern, not a general requirement. The implementation-independent requirement is to prepare stable child-visible causal context before launch and reconcile it with the observable tool execution. A runtime that creates the tool span before launch, or uses another documented causal model, need not use reservation.

When enabled, Pilot's Claude Code `PreToolUse(Bash)` hook runs after the tool call has an identity but before the child process exists:

1. It identifies the session, prompt/turn and `tool_use_id`.
2. It chooses the turn trace context. A valid, not-yet-consumed environment upstream is preferred. An opt-in mode can generate a local trace when upstream context is absent.
3. It reserves a random 8-byte span ID for the future Bash TOOL span.
4. It creates the child's `traceparent` with the selected trace ID and the reserved TOOL span ID as `parent-id`.
5. It prepends shell-safe exports for `TRACEPARENT` and valid `TRACESTATE` to the Bash command.
6. Independently, it maps a Pilot bootstrap input to the standard `OTEL_RESOURCE_ATTRIBUTES` variable immediately before process launch.

The private bootstrap input is an implementation detail used because an agent runtime may sanitize inherited `OTEL_*` variables. It is not proposed as a standard carrier. The boundary output consumed by an OpenTelemetry SDK is the standard `OTEL_RESOURCE_ATTRIBUTES` variable.

### 5.2 Reconciliation with the authoritative transcript

Claude Code's Stop hook later parses the transcript that authoritatively records the tool call and result. Pilot:

1. reuses the trace ID selected before execution for all records in that turn;
2. looks up the reservation by `tool_use_id`;
3. uses the reserved span ID for both the tool-call and tool-result records; and
4. converts them into the observable `execute_tool Bash` span.

This is the central relationship invariant:

```text
child TRACEPARENT.parent-id == emitted Bash TOOL span_id
```

The child process can therefore create its first span under the exact TOOL span that Pilot materializes later.

### 5.3 Concurrency, restart and failure semantics

This implementation pattern also demonstrates boundary-state properties that do not appear in the field formats themselves:

- All Bash calls in one turn share the turn trace ID but reserve distinct TOOL span IDs.
- Duplicate delivery for the same `tool_use_id` is idempotent.
- Shared turn and per-tool records are written completely to a temporary file and atomically published; readers retry briefly when interoperating with an older writer that exposed an incomplete file.
- Consumption of a session-level environment upstream is persisted so a collector restart cannot incorrectly attach a later local turn back to the old upstream trace.
- If an ACP per-turn record already owns trace selection, the hook does not generate or inject a competing local context. Resource bootstrap remains independent.
- Invalid context, malformed state and storage failures are fail-open for the user command.

### 5.4 What the implementation does not claim

The current implementation is intentionally narrow:

- It covers main-agent Claude Code `Bash` calls, including background Bash invocation, but not subagent, PowerShell, MCP or non-Bash tools.
- ACP-only per-turn upstream context cannot yet be mapped reliably to the current `PreToolUse` call, so Pilot suppresses competing Trace Context rather than risk a split trace.
- Local generation requires a stable prompt/turn identifier.
- The downstream CLI must extract the environment carrier, create spans and configure its own exporter; Pilot does not instrument arbitrary child binaries automatically.
- Baggage propagation is not implemented in this path.
- The reservation files provide consistency and idempotency, not tamper-evident audit records.

These limitations are useful gap-analysis evidence rather than hidden implementation details.

## 6. Validation evidence

The merged implementation includes:

- unit tests for valid/invalid context, shell-safe injection, trace flags, resource bootstrap and first-turn consumption;
- multi-process tests for parallel tool calls, duplicate delivery and compatibility with a briefly incomplete record from an older writer;
- collector-restart tests for persistent first-turn-only semantics;
- a Claude Code hook simulator that applies the returned `updatedInput` to a real Bash process;
- a demo child CLI that records the context and Resource bootstrap it actually receives;
- integration tests covering upstream context, generated local context, ACP conflict avoidance, disabled propagation, Stop/transcript reconciliation, TraceLinker processing and OTLP span conversion; and
- successful Node.js 18, 20 and 22 CI, CodeQL and secret scanning on the merged PR.

This test shape matters: checking only the hook response would not prove that the child process received the selected context or that the later TOOL span reused the reserved identity.

## 7. Candidate conformance checklist

An Agent → Tool implementation with a local CLI realization can be assessed with the following checks:

1. **Boundary identification:** Direct Agent → Tool calls are observable even when no Skill exists.
2. **Upstream preservation:** A valid upstream trace ID is preserved when policy permits.
3. **No-upstream behavior:** The behavior when no upstream exists is explicit: generate, start a new trace, or do not propagate.
4. **Pre-execution availability:** Stable child-visible causal context is prepared before the child starts; span-ID reservation is one implementation pattern, not a requirement.
5. **Relationship invariant:** A synchronous in-lifetime child's parent span ID identifies the documented process-launch span—either the tool span in a single-span model or a separate CLI caller span in a nested model—and preserves an unbroken causal path from the Agent → Tool execution. Detached/background work uses a documented relationship, such as a Span Link, when parent/child causality would misrepresent ownership or lifecycle.
6. **Actual-child verification:** Validation checks what the real process received and emitted, not only what the agent or hook declared.
7. **Parallel identity:** Parallel calls follow the documented trace-sharing model and retain distinct span identities.
8. **Retry idempotency:** Duplicate hook, interceptor or launch delivery does not create conflicting identities.
9. **Restart continuity:** Collector/runtime restart does not resurrect consumed context or split a later invocation.
10. **Semantic separation:** Trace Context, Baggage, Resource attributes and tool content are not used interchangeably.
11. **Lifecycle and outcome:** Spawn failure, non-zero exit, timeout, cancellation, retry and background completion are distinguishable.
12. **Privacy and security:** Sensitive arguments, credentials and Baggage are not propagated or recorded by default; child environments are allowlisted and escaped safely.
13. **Fail-open policy:** Observability-state failure does not block the user command unless an explicit enforcement policy says otherwise.
14. **Evidence source and assurance:** Records identify the observer, observation point, how directly the source observed the action and the assurance level. Agent-runtime declarations, hook reservations, OS/process observations and child instrumentation remain distinguishable, and any integrity guarantee is stated explicitly.

## 8. Open gaps and coordinate-first recommendations

### 8.1 Add a non-normative Agent → local CLI composition example upstream

Coordinate with the OpenTelemetry GenAI SIG and Semantic Conventions maintainers on a worked example that combines:

- the GenAI `execute_tool` span;
- CLI caller/callee spans;
- the environment-variable context carrier; and
- Resource bootstrap during child SDK initialization.

The first goal should be guidance and a conformance scenario, not new attributes.

### 8.2 Clarify span ownership and suppression

The WG should ask whether an `execute_tool` span that directly represents a process launch also serves as the CLI caller span, or whether separate nested spans are preferred. The answer should prevent duplicate spans while preserving the exact parent required by the child.

### 8.3 Define an agent-runtime adoption profile

The environment carrier mechanics now have an OpenTelemetry specification. An agent-runtime profile could focus on the missing operational contract:

- expose a lifecycle integration point where stable child context can be prepared before launch;
- inject into a per-child environment rather than mutating global process state;
- preserve normalized propagator keys through runtime sanitization;
- allow policy-based Baggage filtering;
- keep Resource bootstrap separate; and
- verify the actual process boundary.

### 8.4 Extend reference conformance testing

The OpenTelemetry GenAI repository already includes an execute-tool coverage report and reference scenarios. A local CLI subprocess scenario could test the parent/child relationship across a real process boundary. The Pilot simulator and demo CLI show one implementation pattern, but a WG artifact should remain implementation-neutral.

### 8.5 Treat evidence integrity as cross-cutting

Trace continuity does not prove that agent-side or child-side records are complete or trustworthy. A future conformance model should record observer identity, observation point, how directly the source observed the action and the assurance level, and should distinguish ordinary telemetry consistency from tamper-evident evidence. This cross-cutting representation is tracked in [issue #36](https://github.com/aaif/wg-observability-and-traceability/issues/36) and should be coordinated with the Agent → MCP Server deep-dive and existing security/event-integrity work rather than specified independently here.

## 9. Review questions

1. Does the document keep the canonical Agent → Tool semantic boundary distinguishable from its Agent Runtime → Local Process realization, as well as from Skill → Tool and Agent → MCP Server?
2. Should `execute_tool` and CLI caller instrumentation share one span for a direct process launch, or should one suppress/nest the other?
3. Is the Release Candidate environment carrier specification sufficient as the baseline carrier, with the remaining work framed as agent-runtime adoption and conformance?
4. Which invocation-scoped fields, if any, need standardized Baggage semantics rather than product-specific keys?
5. Which lifecycle states are required for background tools, cancellation and retry?
6. What minimum observer attribution or evidence-integrity property belongs in the cross-cutting model?

## 10. Suggested next steps

1. Review this filled pass against issue #29 and the Agent → MCP Server deep-dive.
2. Lift the agreed compact row into the seed matrix in PR #25 or its follow-up.
3. Convert the conformance checklist into an implementation-neutral test plan.
4. Coordinate the execute-tool/CLI composition questions with OpenTelemetry rather than creating a competing convention.
5. Track broader carriers and boundaries—MCP, PowerShell, containers, remote APIs and subagents—as separate follow-up passes.

## References

- [AAIF issue #29: Cross-boundary observability gap model for agentic systems](https://github.com/aaif/wg-observability-and-traceability/issues/29)
- [AAIF PR #25: Cross-boundary observability model](https://github.com/aaif/wg-observability-and-traceability/pull/25)
- [AAIF PR #32: Agent → MCP Server boundary deep-dive](https://github.com/aaif/wg-observability-and-traceability/pull/32)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [W3C Baggage](https://www.w3.org/TR/baggage/)
- [OpenTelemetry environment variables as context propagation carriers](https://opentelemetry.io/docs/specs/otel/context/env-carriers/)
- [OpenTelemetry GenAI execute-tool semantic convention](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md#execute-tool-span)
- [OpenTelemetry execute-tool reference coverage report](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/reference/reports/execute-tool-span.md)
- [OpenTelemetry CLI span conventions](https://opentelemetry.io/docs/specs/semconv/cli/cli-spans/)
- [OpenTelemetry Baggage API](https://opentelemetry.io/docs/specs/otel/baggage/api/)
- [OpenTelemetry Resource SDK](https://opentelemetry.io/docs/specs/otel/resource/sdk/)
- [LoongSuite Pilot PR #316](https://github.com/alibaba/loongsuite-pilot/pull/316)
- [LoongSuite Pilot downstream CLI propagation guide](https://github.com/alibaba/loongsuite-pilot/blob/e3de025a4de31a99056f6bbd1d3a99b322f02061/docs/zh-CN/claude-code-downstream-trace-propagation.md)
- [LoongSuite Pilot pre-execution context implementation](https://github.com/alibaba/loongsuite-pilot/blob/e3de025a4de31a99056f6bbd1d3a99b322f02061/assets/hooks/claude-code/tool-context.mjs)
- [LoongSuite Pilot hook event processor](https://github.com/alibaba/loongsuite-pilot/blob/e3de025a4de31a99056f6bbd1d3a99b322f02061/assets/hooks/claude-code-hook-processor.mjs)
- [LoongSuite Pilot hook simulator integration test](https://github.com/alibaba/loongsuite-pilot/blob/e3de025a4de31a99056f6bbd1d3a99b322f02061/tests/integration/claude-code-tool-context-flow.test.mjs)
