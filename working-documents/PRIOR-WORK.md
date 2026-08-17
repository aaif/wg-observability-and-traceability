# Prior Work in Agent Observability

**AAIF Observability Working Group - Landscape Survey**
**Initial draft:** 2026-03-15
**Status:** Living working group document - last reviewed 2026-07-08

---

## Purpose

This document surveys the existing proposals, specifications, and implementations related to agent observability. The goal is to give working group members a shared understanding of what exists today, how mature each effort is, and where there are opportunities for collaboration or extension.

This is not a competitive ranking - many of these efforts address different facets of the same problem space. We include them all because the working group should be aware of the full landscape.

## Context: The AAIF and This Working Group

The Agentic AI Foundation (AAIF), formed in December 2025 under the Linux Foundation, is the home of MCP, goose, AGENTS.md, Agentgateway, A2A (agent-to-agent interoperability, joined August 2026), and AGNTCY (multi-agent standards for discovery, identity, messaging, and observability). Its platinum members include AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, and OpenAI, with 97+ additional members including Cisco, Datadog, Docker, IBM, JetBrains, Okta, Oracle, Salesforce, SAP, and Shopify. The Observability Working Group operates under this umbrella, with the mandate to survey, coordinate, and where appropriate standardize agent observability across the AAIF community.

We are not starting from scratch. As this survey shows, there is substantial prior work across multiple organizations and standards bodies. Our job is to understand what exists, identify gaps, and determine where AAIF can add the most value - whether that's adopting existing standards, extending them, or filling genuinely unaddressed needs.

---

## June 2026 Refresh Notes

This refresh keeps the March 2026 landscape structure but updates the areas where the industry moved materially:

- **OpenTelemetry GenAI is now its own standards venue.** The main OTel semantic-conventions docs now point readers to the dedicated [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) repository. That repo contains the generated GenAI docs for agent/framework spans, events, MCP, provider-specific conventions, and a reference implementation/compliance matrix.
- **Agent spans are becoming more explicit.** OTel GenAI now documents create-agent, invoke-agent, invoke-workflow, execute-tool, and plan spans. The work remains in Development status, but the model is more concrete than it was in March.
- **Cursor Agent Trace remains narrow and draft-stage.** The public repo still presents v0.1.0 as the draft format; as of 2026-06-16, repository metadata showed 744 stars, 54 forks, 19 open issues, and no published GitHub release.
- **AOS has a clearer specification surface.** The AOS site now separates Instrument, Trace, and Inspect specs, including MCP/A2A instrumentation, OpenTelemetry and OCSF trace mappings, and AgBOM mappings to CycloneDX/SPDX/SWID.
- **AGNTCY Observe is worth tracking closely.** The Observe SDK docs describe an OTel-aligned multi-agent observability schema, protocol instrumentation for A2A, SLIM, and MCP, and end-to-end trace recomposition across agent boundaries. The `agntcy/observe` repo has published `sdk-v1.0.42`.
- **Implementation ecosystems are still moving quickly.** Monocle reached v0.8.4 in June 2026. OpenInference, Langfuse, Helicone, and related observability platforms continue to evolve rapidly, reinforcing that this document needs periodic refreshes rather than one-time publication.
- **Environment-derived telemetry is relevant to agent observability.** OTel's eBPF instrumentation work, including OBI, is not GenAI-specific but can provide trusted network and runtime signals that complement telemetry emitted by agents or frameworks.
- **Academic work is shifting toward security and governance.** Recent 2026 papers frame agent observability as a substrate for continuous security monitoring and closed-loop governance, not only debugging and evaluation.

## Summary Table

| Initiative | Scope | Maturity | Open/Proprietary | Key Strength |
|------------|-------|----------|-------------------|--------------|
| **OTel GenAI Semantic Conventions** | LLM, agent, workflow, tool, MCP spans/events/metrics | Development; moved to dedicated GenAI repo | Open (Apache 2.0) | Broad industry backing, existing OTel ecosystem |
| **OTel GenAI SIG - Agentic Systems Proposal** | Tasks, actions, teams, memory | Active proposal (now in `semantic-conventions-genai`) | Open | Multi-agent modeling |
| **Agent Trace (Cursor)** | AI code attribution | Draft RFC (v0.1.0; repo quiet since Feb 2026) | Open (CC BY 4.0) | Coding tool adoption, simplicity |
| **OWASP Agent Observability Standard (AOS)** | Security-focused instrument/trace/inspect model | Active draft/spec site | Open | Security and compliance framing |
| **OpenInference (Arize)** | LLM/RAG span instrumentation | Production use | Open (Apache 2.0) | Practical, OTel-compatible |
| **OpenLLMetry (Traceloop)** | LLM provider instrumentation | Production use | Open (Apache 2.0) | Broad provider coverage |
| **LangSmith (LangChain)** | Full-stack LLM observability | Production | Proprietary (OTel export) | Deep LangChain integration |
| **Arize Phoenix** | LLM/agent observability platform | Production | Open (self-hostable) | End-to-end: tracing + eval |
| **MLflow Tracing** | LLM/agent tracing in ML platform | Production | Open (Apache 2.0) | 30M+ monthly downloads, Databricks ecosystem |
| **W&B Weave** | LLM observability + RL trajectories | Production | SDK open / backend proprietary | Unified MLOps + LLMOps |
| **Langfuse** | LLM observability with published data model | Production | Open source | OTel-native, session-aware, self-hostable |
| **Helicone** | Proxy-based LLM observability | Production | Open source | Zero-SDK integration, 2B+ interactions |
| **Monocle (LF AI & Data)** | GenAI auto-instrumentation framework | Early, active (v0.8.4) | Open (Apache 2.0) | Broadest framework auto-instrumentation |
| **AGNTCY** | Multi-agent interop + observability | Active; Observe SDK 1.0.x | Open (Apache 2.0) | Cross-agent context propagation |
| **A2A** | Agent-to-agent protocol (v1.0, Mar 2026); signed agent cards, task delegation | Production (Huawei Celia, WeChat, Google Cloud ADK, Azure AI Foundry, AWS Bedrock AgentCore, PayPal) | Open (Apache 2.0) | Cross-vendor agent interoperability; signed agent identity |
| **agentgateway** | Traffic mediation/control between agents and infrastructure (MCP + A2A) | One-click deployable on AWS/Azure/GCP marketplaces | Open (Apache 2.0) | Central enforcement point for declared-vs-observed policy |
| **OpenLIT** | OTel-native LLM observability | Production | Open | Follows OTel semconv closely |
| **OBI / OTel eBPF instrumentation** | Network/runtime instrumentation signals | Active OTel effort | Open | Trusted environment-derived telemetry |
| **ATIF trajectory format** | Session-level trajectory artifact | RFC/proposal | Open | Interchangeable trajectory data for eval/training/replay |

---

## Detailed Assessments

### 1. OpenTelemetry GenAI Semantic Conventions

**What it is:** The OpenTelemetry project's official semantic conventions for generative AI systems - defining standard attribute names, span structures, event payloads, and metric conventions for LLM calls, agent invocations, workflows, tool use, and MCP interactions. As of June 2026, the GenAI work has moved from the main semantic-conventions docs into the dedicated [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai) repository.

**Scope:**
- GenAI client spans (LLM calls): `chat`, `embeddings`, `retrieval` operations with model name, token usage, temperature
- Agent/framework spans: `create_agent`, `invoke_agent`, `invoke_workflow`, `plan`, and `execute_tool` spans with span kind guidance (CLIENT for remote services, INTERNAL for in-process work)
- **MCP conventions** (directly relevant to AAIF): dedicated semantic conventions for Model Context Protocol with W3C trace context propagation via `params._meta.traceparent`. Defines `mcp.method.name`, `mcp.session.id`, and session duration metrics. Example canonical trace:
  ```
  invoke_agent weather-forecast-agent (INTERNAL)
   |-- chat {model} (CLIENT)
   |-- tools/call get-weather (CLIENT)          # MCP client
       |-- tools/call get-weather (SERVER)      # MCP server
   |-- chat {model} (CLIENT)
  ```
- Events (via Logs API): `gen_ai.client.inference.operation.details` captures full chat history, tool definitions, parameters. Opt-in, sensitive content not captured by default. `gen_ai.evaluation.result` for quality scores.
- Metrics: token usage, operation duration, time-to-first-token, time-per-output-token
- Technology-specific conventions for: Anthropic, Azure AI Inference, AWS Bedrock, OpenAI
- Three signal types: traces, metrics, and events

**Maturity:** The GenAI semantic conventions remain in **Development** status (not yet stable). The dedicated GenAI repository has no published GitHub release as of 2026-06-16, but it is active and now includes generated docs plus a reference implementation/compliance matrix. The old main OTel semconv page is explicitly marked as moved and no longer maintained there.

**Key contributors:** Engineers from Amazon, Elastic, Google, IBM, Langtrace, Microsoft, OpenLIT, Scorecard, Traceloop, and others. Microsoft and Cisco (Outshift) have been particularly active in enhancing multi-agent observability conventions based on W3C Trace Context.

**Strengths:**
- Broadest industry coalition of any effort in this space
- Built on the proven OTel distributed tracing model
- Natural home for standardization - OTel is already the de facto standard for application observability
- Three-signal approach (traces, metrics, events) is more comprehensive than trace-only efforts

**Gaps (from the working group's perspective):**
- Span attribute size limits make it difficult to capture full message content, which is essential for many agent observability use cases (debugging, evaluation, replay). The spec moved content to Events (Logs API), but Events are still experimental and unevenly supported across platforms. OpenInference took the opposite approach (attributes on spans), which explains its popularity despite not being the OTel standard.
- The conventions model agents as span trees, which works well for request-response patterns but may not capture the full richness of long-running, multi-turn agent sessions
- No turn-level structure - agent interactions are modeled as spans rather than as structured multi-turn conversations
- Agent framework conventions not standardized (Issue #1530, open, in backlog) - CrewAI, LangGraph, AutoGen all instrument differently
- No standard for agent-to-agent communication tracing beyond W3C trace context propagation
- No annotation or evaluation layer beyond a basic `gen_ai.evaluation.result` event
- No cost modeling beyond token counts
- `gen_ai.conversation.id` exists but there's nothing for persisted memory across sessions or multi-session correlation
- The repository move improves focus but makes the status boundary between core OTel and GenAI-specific conventions less obvious to casual readers

**Interaction opportunity:** High. OTel is the natural venue for runtime telemetry conventions. The working group should engage directly with the GenAI SIG and the dedicated GenAI repository. The question is whether agent observability needs only extend the existing span model, or whether it requires complementary formats for richer use cases (evaluation, replay, cost analysis).

**References:**
- [OpenTelemetry GenAI Semantic Conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)
- [GenAI agent and framework spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)
- [GenAI events](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md)
- [AI Agent Observability Blog Post](https://opentelemetry.io/blog/2025/ai-agent-observability/)

---

### 2. OTel Agentic Systems Proposal (Issue #2664)

**What it is:** A proposal within the OTel semantic conventions repo to define conventions for observability of generative AI agentic systems - going beyond individual LLM calls to model the higher-level structures of agent workflows.

**Scope:** Defines attributes for:
- **Tasks** - minimal trackable units of work, decomposable into subtasks
- **Actions** - how tasks are carried out (tool calls, LLM queries, API requests, vector DB queries, human input, workflows)
- **Agents** - the entities executing tasks
- **Teams** - dynamic groups of agents collaborating toward shared goals
- **Artifacts** - outputs produced by agent work
- **Memory** - persistent and scoped storage of knowledge and context

**Maturity:** Proposal stage, now tracked in the dedicated `semantic-conventions-genai` repository after the original OTel semantic-conventions issues were redirected. The broad agentic systems proposal is now issue #35, and the task taxonomy proposal is now issue #37. Some concrete agent/framework spans (including workflow and plan spans) now appear in the generated docs, but the full task/action/team/artifact/memory model is not yet stable.

**Related work:** Microsoft and Cisco (Outshift) contributed multi-agent conventions (October 2025) including agent reasoning spans, tool invocation spans, and inter-agent messaging spans (delegation, handoff, result streaming). These are live in Azure AI Foundry and work across Microsoft Agent Framework, LangChain, LangGraph, and OpenAI Agents SDK. Framed around the "Internet of Cognition" / AGNTCY project (donated to Linux Foundation).

**Strengths:**
- Addresses the multi-agent coordination problem that simpler specs ignore
- Models memory and artifacts as first-class concepts
- Explicitly designed for complex, multi-step AI workflows
- Has active industry backing (Microsoft, Cisco)

**Gaps:**
- Still at the proposal stage - significant design work remains
- The task/action decomposition may be too opinionated for some agent architectures
- Cisco flagged overlap with existing workflow/task concepts (Issue #1688)
- No reference implementation yet

**Interaction opportunity:** High. This proposal is actively seeking input. Working group members building multi-agent systems should review and contribute. The AGNTCY connection to Linux Foundation means there's a natural bridge to AAIF.

**References:**
- [GitHub Issue #35 - Agentic Systems](https://github.com/open-telemetry/semantic-conventions-genai/issues/35)
- [GitHub Issue #37 - Tasks](https://github.com/open-telemetry/semantic-conventions-genai/issues/37)
- [GitHub Issue #1530 - Agent Framework Convention](https://github.com/open-telemetry/semantic-conventions/issues/1530)

---

### 3. Agent Trace (Cursor)

**What it is:** An open specification for tracking AI-generated code, published by Cursor in January 2026. It defines a vendor-neutral JSON format for recording which code was written by humans vs. AI, at file and line granularity.

**Scope:** Code attribution only - which model produced which lines of code, in which session, at which time. The spec is intentionally narrow:
- Trace records (`application/vnd.agent-trace.record+json`) with version, ID (UUID), timestamp (RFC 3339), and file-level attribution
- `files` array with `conversations` containing `contributor` type (human/ai/mixed/unknown), optional `model_id`, and line `ranges`
- Model identifiers following the models.dev convention (`provider/model-name`)
- `content_hash` (murmur3) at the range level for tracking code movement across files
- VCS support for git, jj (Jujutsu), hg, and svn
- Extensible metadata using reverse-domain notation (e.g., `dev.cursor`, `com.github.copilot`) for vendor-specific data
- Storage-agnostic (local files, git notes, databases - implementation decides)

**What it explicitly does NOT cover:**
- Legal ownership or copyright
- Training data provenance
- Code quality evaluation
- The agent's decision process, failed attempts, or cost

**Maturity:** Draft RFC (v0.1.0). Reference implementation in TypeScript (`trace-store.ts`, `trace-hook.ts`). 744 GitHub stars, 54 forks, 19 open issues as of 2026-06-16. The public repo's last push was 2026-02-06 and it has no published GitHub release, so the format still appears to be in the "get everyone aligned on the format" phase rather than a stable release phase.

**Partners:** Amp, Amplitude, Cline, Cloudflare, Cognition (Devin), git-ai, Jules (Google), OpenCode, Tapes, Vercel. This is a strong coalition of coding tool vendors. Cognition published a supporting blog post framing Agent Trace as the foundation of "context graphs" - arguing that attribution data from prior agent runs becomes a performance multiplier when reused as context (citing 40-80% cache hit rate improvements).

**Active design discussions (open issues):**
- Issue #6: RFC for native OpenTelemetry representation - mapping Agent Trace to OTel spans + `agent_trace.*` attributes. This would enable OTLP export to any backend and unified queries across attribution and runtime data. Unresolved.
- Issue #11: No way to record AI-deleted lines (only additions/modifications)
- Issue #25: Rebase/amend lifecycle - how traces survive VCS rewrites
- Issue #26: Conversation URL durability and privacy
- Issue #27: Ambiguous "mixed" contributor semantics

**Strengths:**
- Clear, narrow scope that's easy to implement
- Strong adoption coalition among coding-focused AI tools
- Practical and immediately useful for code review and compliance workflows
- The "who wrote this code?" question has clear business value
- Jujutsu VCS support is forward-looking (jj change IDs are stable across rebase)

**Gaps (from the working group's perspective):**
- Captures only the output (code attribution) - not the process (agent reasoning, tool use, cost, failed attempts)
- Limited to code-producing agents - doesn't generalize to DevOps agents, monitoring agents, or other non-coding agent types
- No concept of agent sessions, turns, or decision streams
- No support for non-code side effects (API calls, resource creation, process management)
- Line number fragility - ranges reference positions at a recorded VCS revision; queries require `git blame` to map to current positions
- OTel alignment still unresolved - risk of two parallel ecosystems (Agent Trace JSON vs. OTel spans for agent execution)

**Interaction opportunity:** Medium. Agent Trace and broader agent observability are complementary - Agent Trace answers "who wrote this code?" while agent observability answers "how did the agent decide to write it?" A working group deliverable could explore how attribution data and behavioral observability data relate. The open Issue #6 (OTel mapping) is a natural convergence point.

**References:**
- [agent-trace.dev](https://agent-trace.dev/)
- [GitHub: cursor/agent-trace](https://github.com/cursor/agent-trace)
- [Cognition: Agent Trace - Capturing the Context Graph of Code](https://cognition.ai/blog/agent-trace)
- [InfoQ coverage](https://www.infoq.com/news/2026/02/agent-trace-cursor/)

---

### 4. OWASP Agent Observability Standard (AOS)

**What it is:** An OWASP project defining an observability standard for AI agents, with the goal of transforming agents from black boxes into auditable systems suitable for enterprise deployment. It builds on existing standards rather than inventing new ones.

**Three core pillars:**
- **Inspectable** - what tools, models, capabilities, versions, and data sources are in play. Introduces the concept of an Agent Bill of Materials (AgBOM), building on CycloneDX/SWID/SPDX.
- **Traceable** - every action traceable back to its reasoning and originating task. Built on OpenTelemetry and OCSF (Open Cybersecurity Schema Framework).
- **Instrumentable** - runtime intervention capability with hard controls, not just soft guardrails. Leverages MCP and A2A for instrumentation.

**OTel extension model:** AOS defines a turn/step hierarchy mapped onto OTel spans:
- A session encompasses multiple turns (one span per turn)
- Within a turn, each atomic step becomes a child span: `steps/message`, `steps/agentTrigger`, `steps/toolCallRequest`, `steps/toolCallResult`, memory accesses, etc.
- Step IDs from the AOS `RequestContext` (`agent`, `session`, `turnId`, `stepId`) become span attributes
- The `reasoning` field in each step maps to custom span attributes like `agent.thought`
- This is not a competing fork - it is a semantic convention and span-kind taxonomy layered on top of valid OTLP traces

**Maturity:** Active OWASP project with published spec documents. More developed than the initial assessment might suggest - the spec site now presents Instrument, Trace, and Inspect sections, including MCP/A2A instrumentation, OpenTelemetry and OCSF trace mappings, and AgBOM mappings to CycloneDX, SPDX, and SWID. The public GitHub repo has no published release as of 2026-06-16, so the work should still be treated as draft.

**Strengths:**
- Security-first framing fills a gap that other specs don't address directly
- Composable design - builds on OTel, MCP, A2A, OCSF, CycloneDX rather than reinventing
- AgBOM concept (dynamic agent bill of materials) is unique and valuable for enterprise deployment
- Turn/step span hierarchy provides a practical OTel mapping for agent sessions
- OWASP's brand brings credibility in the security and compliance community

**Gaps:**
- Community size is smaller than OTel GenAI SIG
- Security/compliance focus may limit awareness among teams primarily concerned with performance or cost optimization
- The AgBOM concept is novel but untested at scale

**Interaction opportunity:** High. AOS is arguably the most aligned effort with the working group's scope - it addresses agent observability end-to-end (not just LLM calls), builds on standards the AAIF cares about (MCP, A2A), and brings the security/compliance perspective that enterprise adopters need. The turn/step hierarchy is a practical model worth evaluating.

**References:**
- [aos.owasp.org](https://aos.owasp.org/)
- [Trace with OpenTelemetry spec](https://aos.owasp.org/spec/trace/extend_opentelemetry/)
- [Instrument MCP](https://aos.owasp.org/spec/instrument/instrument_mcp/)
- [Instrument A2A](https://aos.owasp.org/spec/instrument/instrument_a2a/)
- [OWASP Project Page](https://owasp.org/www-project-agent-observability-standard-2/)

---

### 5. OpenInference (Arize)

**What it is:** An open semantic convention and span-kind taxonomy for AI application observability, layered on top of OpenTelemetry. Every OpenInference trace is a valid OTLP trace. Natively supported by Arize Phoenix but usable with any OTLP-compatible backend.

**Key design:**
- Signature attribute: `openinference.span.kind` (required on all spans) with values: `LLM`, `EMBEDDING`, `CHAIN`, `RETRIEVER`, `RERANKER`, `TOOL`, `AGENT`, `GUARDRAIL`, `EVALUATOR`, `PROMPT`
- Attribute namespaces: `llm.*` (messages, token counts, model), `tool.*` (name, description, parameters), `retrieval.*`, `embedding.*`, `session.id`, `user.id`
- Multi-turn message arrays: `llm.input_messages.<index>.message.role` / `.content`
- Cache-aware token counts: `llm.token_count.prompt_details.cache_read` / `.cache_write`

**How it differs from OTel GenAI semconv:**

| Dimension | OpenInference | OTel GenAI semconv |
|-----------|--------------|-------------------|
| Attribute prefix | `llm.*`, `openinference.*`, `tool.*` | `gen_ai.*` |
| Span kinds | Custom AI kinds (LLM, CHAIN, AGENT, RETRIEVER, GUARDRAIL, EVALUATOR) | Standard OTel kinds (CLIENT, SERVER, INTERNAL) |
| Scope | Full AI app lifecycle including chains, RAG, guardrails, evaluators | Individual GenAI provider interactions |
| Governance | Community/Arize-led | Official OTel SIG |

**Maturity:** Production use. Actively maintained, used by Arize Phoenix and integrated with multiple frameworks (LangChain, LlamaIndex, DSPy, OpenAI Agents SDK, Claude Agent SDK, AWS Strands Agents, etc.). As of 2026-06-16, the `Arize-ai/openinference` repo had 1,029 stars and had published a new Strands Agents instrumentation release on 2026-06-11.

**Standards convergence:** Arize has donated OpenInference work toward OpenTelemetry GenAI convergence. This makes OpenInference both useful prior art and an active input to the longer-term OTel GenAI standardization path.

**Strengths:**
- Battle-tested in production observability workflows
- Broader span kind vocabulary than OTel GenAI semconv (GUARDRAIL, EVALUATOR, RERANKER are valuable additions)
- Covers the full RAG pipeline well
- OTel-compatible - emits standard OTLP data
- Auto-instrumentors for popular frameworks reduce integration effort

**Gaps:**
- Focused on LLM application observability rather than autonomous agent behavior
- No session-level model - individual calls, not multi-turn sessions
- Spec is maintained by a single vendor (Arize), though it's open source
- Attribute namespace (`llm.*`) overlaps with but differs from OTel's `gen_ai.*` - a potential source of confusion

**Interaction opportunity:** Medium. OpenInference demonstrates practical conventions that work at production scale. The working group can learn from what's been battle-tested here. The span kind vocabulary (especially GUARDRAIL, EVALUATOR) is worth considering for broader adoption. The divergence from OTel GenAI semconv namespace is a cautionary example of fragmentation risk.

**References:**
- [GitHub: Arize-ai/openinference](https://github.com/Arize-ai/openinference)
- [OpenInference Semantic Conventions spec](https://arize-ai.github.io/openinference/spec/semantic_conventions.html)
- [OTel community issue: OpenInference donation](https://github.com/open-telemetry/community/issues/3467)

---

### 6. OpenLLMetry (Traceloop)

**What it is:** An open-source extension to OpenTelemetry providing instrumentation libraries for LLM providers (OpenAI, Anthropic, Cohere, etc.) and vector databases (Pinecone, Chroma, Qdrant, Weaviate). Available in Python and TypeScript.

**Maturity:** Production use. Integrates with Datadog, New Relic, Sentry, Honeycomb, and other backends. Traceloop is now part of ServiceNow, which may affect future project direction and should be tracked in later refreshes.

**Strengths:**
- Broadest provider coverage of any open instrumentation library
- True OTel-native approach - outputs standard OTLP, works with any OTel-compatible backend
- Low-friction adoption (auto-instrumentation, minimal code changes)
- Apache 2.0 licensed

**Gaps:**
- Focused on individual LLM call instrumentation, not agent-level behavior
- No agent session model
- Maintained primarily by Traceloop (single vendor)

**Interaction opportunity:** Low-medium. OpenLLMetry is an implementation library rather than a specification, but it demonstrates the value of OTel-native instrumentation and has influenced the OTel GenAI SIG's direction.

**References:**
- [GitHub: traceloop/openllmetry](https://github.com/traceloop/openllmetry)
- [openllmetry.org](https://www.traceloop.com/openllmetry)

---

### 7. LangSmith (LangChain)

**What it is:** A commercial observability and evaluation platform for LLM applications, built by LangChain. It provides deep tracing with a run-tree data structure, evaluation tools, prompt management, and dataset management.

**Maturity:** Production. Billable since July 2024. Supports Python, TypeScript, Go, and Java SDKs. Handles over 1 billion trace logs.

**Trace model:** Parent-child run tree with nested spans. Each run captures inputs, outputs, errors, model names, latency, and cost. Supports both LangChain-native decorators (`@chain`, `@traceable`) and framework-agnostic tracing via OpenTelemetry export.

**Strengths:**
- Most mature and widely adopted LLM observability platform
- Deep integration with the LangChain ecosystem
- OTel export support bridges the proprietary/open gap
- Rich evaluation framework built on top of traces

**Gaps:**
- Proprietary trace format (not an open spec that others can implement)
- OTel support is for export, not native - the internal format is LangSmith-specific
- Tightly coupled to LangChain's abstractions (Runnables, chains)
- No open spec for the run-tree format itself

**Interaction opportunity:** Medium. LangChain is an important ecosystem player. The working group should consider whether LangSmith's run-tree model (or elements of it) should influence our thinking, even though the format itself is proprietary. OTel interop is the likely bridge.

**Reference:** [langchain.com/langsmith](https://www.langchain.com/langsmith)

---

### 8. Arize Phoenix

**What it is:** An open-source, self-hostable observability and evaluation platform for LLM applications and AI agents. Built on OpenTelemetry and OpenInference.

**Maturity:** Production. Active development, strong community. Supports OpenAI Agents SDK, Claude Agent SDK, LangGraph, Vercel AI SDK, CrewAI, LlamaIndex, DSPy, and more.

**Strengths:**
- Fully open source and self-hostable (no feature gates)
- End-to-end: tracing, evaluation, prompt management, datasets, experiments
- Vendor and framework agnostic via OTel
- Captures the full agent reasoning loop (LLM calls, tool executions, retrieval operations)

**Gaps:**
- Platform, not a spec - the value is in the product, not a portable format
- Evaluation methodology is Phoenix-specific
- No formal session specification

**Interaction opportunity:** Low-medium. Phoenix is a consumer of whatever standards emerge, not a standards body. But it demonstrates what practitioners need from agent observability tooling.

**Reference:** [phoenix.arize.com](https://phoenix.arize.com/)

---

### 9. MLflow Tracing

**What it is:** MLflow 3.x's LLM/agent tracing capability, built into the widely-used ML experiment tracking platform. Supports auto-tracing via `mlflow.<library>.autolog()` for LangChain, OpenAI, LlamaIndex, DSPy, AutoGen, and more.

**Maturity:** High and accelerating. 30M+ monthly downloads. MLflow 3.9.0 (2025) added AI observability dashboards, distributed tracing, and continuous monitoring. Agent-specific DAG capture (parallel tool calls, conditional branches) added in 2025.

**Strengths:**
- Existing MLflow users get agent tracing for free
- Tight integration with Databricks ecosystem
- Strong eval and experiment tracking heritage
- OTel-compatible for export

**Gaps:**
- Agent observability was added to an ML-first platform - less agent-native than purpose-built tools
- Internal trace format is MLflow-specific, not a published open spec

**Interaction opportunity:** Low-medium. MLflow is a consumer of standards, not a standards producer. But its massive user base means any standard the working group defines should be interoperable with MLflow's trace model.

**Reference:** [MLflow Tracing Docs](https://mlflow.org/docs/latest/genai/tracing/)

---

### 10. W&B Weave

**What it is:** Weights & Biases' LLM observability and evaluation toolkit. Decorator-based (`@weave.op`) approach that captures function inputs/outputs into a trace tree organized by call stack hierarchy.

**Maturity:** Production-ready. Integrated with AWS Bedrock AgentCore (announced 2025).

**Strengths:**
- Unified MLOps + LLMOps story (train and observe in one platform)
- RL trajectory inspection - useful for fine-tuning from agent sessions
- Planning/reasoning trace visibility, handoff tracing for multi-agent

**Gaps:**
- Proprietary backend and trace format, not OTel-native
- Primarily Python-centric

**Interaction opportunity:** Low. Proprietary format unlikely to converge with open standards, but the RL trajectory use case is worth noting in our use case inventory.

**Reference:** [Weave Docs](https://docs.wandb.ai/weave)

---

### 11. Langfuse

**What it is:** Open-source LLM observability platform with a published data model. OTel-native. Postgres + ClickHouse backend. Often cited as the leading open-source alternative to LangSmith.

**Maturity:** Production use. YC W23. Published data model with sessions, traces, observations (spans/generations/events), and scores. As of 2026-06-16, Langfuse was in the v3.x release line (`v3.187.0`) and the public repo remained highly active.

**Strengths:**
- Open source with a published, documented data model
- OTel-native integration (both ingest and export)
- Session concept as a first-class grouping mechanism
- Self-hostable with standard infrastructure (Postgres + ClickHouse)

**Gaps:**
- Session model is simpler than what may be needed for complex agent workflows
- No agent-specific span taxonomy (compared to OpenInference)

**Interaction opportunity:** Medium. Langfuse's published data model is a good reference for what a practical session-aware trace model looks like. Their OTel integration approach is worth studying.

**Reference:** [Langfuse Data Model](https://langfuse.com/docs/observability/data-model)

---

### 12. Emerging Startups (AgentOps, HoneyHive, Helicone)

These represent the startup wave in agent observability. Each has a distinct angle:

- **AgentOps** - Agent-first observability with time-travel debugging and session replay. Supports 400+ LLMs. Notable feature: saved completions for fine-tuning. Python-only, cloud-only.
- **HoneyHive** - Enterprise focus with human-in-the-loop evaluation. SOC 2, HIPAA, GDPR compliance. OTel-based tracing. Closed source, enterprise pricing.
- **Helicone** - Proxy-based approach (URL change, no SDK). Open source (YC W23). Built on Cloudflare Workers + ClickHouse + Kafka. 2B+ LLM interactions processed. Built-in caching is unique. Very low overhead (50-80ms).

**Architectural note:** Helicone's proxy approach vs. AgentOps/HoneyHive's SDK approach represents a real design tension - proxy gives low coupling and universal compatibility but limited depth; SDK gives rich semantics but tighter coupling.

**Interaction opportunity:** Low individually, but collectively they demonstrate the market's demand for agent observability and the diversity of approaches being tried.

---

### 13. Microsoft VS Code - Native OTel for Agent Observability

**What it is:** A proposal (GitHub Issue #293225) for native OpenTelemetry instrumentation in VS Code's Copilot Chat - instrumenting the agent runtime and tool execution directly with OTel GenAI conventions and emitting OTLP.

**Targets:** Run/session root span, tool-call spans, and LLM request spans/events (model, latency, tokens, cache).

**Maturity:** Proposal stage.

**Interaction opportunity:** Medium. Microsoft is a major player and their approach to agent observability in Copilot will influence the ecosystem. Worth tracking.

**Reference:** [microsoft/vscode#293225](https://github.com/microsoft/vscode/issues/293225)

---

### 14. Monocle (LF AI & Data)

**What it is:** A community-driven open-source framework for auto-instrumenting GenAI and agentic applications. Monocle wraps popular frameworks (LangGraph, LlamaIndex, CrewAI, Google ADK, OpenAI Agent SDK, AWS Strands, Microsoft Agent Framework) with automatic instrumentation, capturing spans for inference calls, retrieval operations, tool invocations, and workflow steps - without requiring developers to write custom OTel code.

**Maturity:** LF AI & Data Sandbox project (accepted August 2024). Current version v0.8.4 (published 2026-06-08). Pre-1.0, but rapidly gaining framework coverage. A separate `monocle-specs` repo defines the GenAI metamodel.

**Relationship to OTel:** OTel-adjacent. Emits spans in an OTel-compatible format and works with OTel collectors, but the core value is a GenAI-specific metamodel that abstracts away the need for developers to manually implement OTel GenAI conventions. Not trying to replace OTel - it's a ready-made instrumentation layer that outputs to OTel.

**Strengths:**
- Broadest framework auto-instrumentation coverage of any single project
- Includes a GenAI test tool for validating expected agent/tool call behavior against captured traces
- LF AI & Data governance provides vendor neutrality

**Gaps:**
- Pre-1.0, sandbox stage
- Metamodel is Monocle-specific - not yet aligned with OTel GenAI semconv

**Interaction opportunity:** Medium-high. Monocle operates in the same foundation ecosystem (Linux Foundation) and is directly focused on the instrumentation problem. The metamodel in `monocle-specs` is worth reviewing for conventions the WG could adopt or influence.

**References:**
- [GitHub: monocle2ai/monocle](https://github.com/monocle2ai/monocle)
- [Metamodel specs](https://github.com/monocle2ai/monocle-specs)
- [LF AI & Data announcement](https://lfaidata.foundation/blog/2024/08/19/lf-ai-data-announces-monocle-as-its-latest-sandbox-project/)

---

### 15. AGNTCY

**What it is:** An open infrastructure project for multi-agent interoperability, originally open-sourced by Cisco (March 2025), then donated to the Linux Foundation (July 2025). Describes itself as building the "Internet of Agents" - shared infrastructure so AI agents built by different vendors can discover, communicate with, and trust each other. The Linux Foundation announcement described 65+ supporting companies and highlighted discovery, identity, messaging, and observability as core project features.

**Scope:** Six components: OASF (agent schema), Agent Directory (decentralized discovery), SLIM (secure messaging), Observe SDK (OTel-based tracing), Identity (decentralized agent identity), and Security (auth and encryption).

**Observability scope specifically:** The Observe SDK is an OTel extension with multi-agent-specific semantic conventions. Key capabilities:
- Framework-agnostic OTel-compliant instrumentation via decorators or native OTel primitives
- Cross-agent context propagation to reconstruct end-to-end traces spanning multiple autonomous agents
- Multi-agent-specific metrics: collaboration success rate, response time, task delegation accuracy
- Schema translation layer to normalize telemetry from heterogeneous OTel-compliant SDKs

**Maturity:** Active and still evolving rapidly. The Observe SDK docs describe an OTel-aligned multi-agent observability schema, protocol instrumentation for A2A, SLIM, and MCP, and end-to-end trace recomposition across agent boundaries. The `agntcy/observe` repo has published `sdk-v1.0.42` (2026-05-28).

**Strengths:**
- Observability is one of six explicit pillars, not an afterthought
- Addresses the hardest part of multi-agent observability: cross-boundary context propagation
- LF governance and strong backer list

**Gaps:**
- Sub-1.0, still evolving rapidly
- Observe SDK adoption is nascent

**Interaction opportunity:** High. AGNTCY is under the same Linux Foundation umbrella, observability is a core pillar, and the cross-agent tracing problem is one the WG should understand deeply. The Observe SDK's conventions should be reviewed alongside OTel GenAI SIG proposals.

**References:**
- [agntcy.org](https://agntcy.org/)
- [Observe SDK docs](https://docs.agntcy.org/obs-and-eval/observe-sdk/)
- [LF announcement](https://www.linuxfoundation.org/press/linux-foundation-welcomes-the-agntcy-project-to-standardize-open-multi-agent-system-infrastructure-and-break-down-ai-agent-silos)

---

### 16. Adjacent Standards and Formats (CloudEvents, OpenLineage, OBI, ATIF)

These are not all agent observability specifications, but they operate in adjacent layers that the WG should be aware of.

**CloudEvents (CNCF, Graduated):** A vendor-neutral envelope format for event data, standardizing how event metadata (source, type, subject, time, ID) is expressed and transported. Production-grade (v1.0.2), adopted by AWS EventBridge, Azure Event Grid, Google Eventarc, and others. Relevant to agent observability as a potential transport envelope for agent events in event-driven multi-agent architectures (e.g., Kafka-based agent buses). No current effort to standardize AI agent-specific CloudEvents schemas.

**OpenLineage (LF AI & Data, Graduated):** An open standard for collecting lineage metadata about data pipeline runs. Defines Job, Run, and Dataset entities with extensible facets. Widely adopted for SQL/Spark/Airflow/dbt pipeline lineage. Relevant to agent observability because it tracks "what data did the agent's pipeline consume and produce" - the data layer beneath agent reasoning. The Run/Job/Dataset model maps interestingly onto agentic systems (workflow = Job, execution = Run, tool outputs = Datasets), but this mapping has not been formalized.

**OpenTelemetry eBPF Instrumentation / OBI:** OBI is part of OpenTelemetry's eBPF instrumentation work. It is not specific to GenAI or agent observability, but it can provide network-level and runtime-derived telemetry that may be more trustworthy than agent-emitted signals for some security, safety, and compliance use cases.

**ATIF trajectory format:** The ATIF trajectory format proposed in the Harbor RFC is relevant to the WG's session-level trajectory question. It may be useful as an interchangeable session artifact derived from OTel traces, especially for training, evaluation, and replay workflows that need more than individual spans.

**Interaction opportunity:** Low for direct adoption, but worth tracking. CloudEvents may matter if the WG defines event-based conventions for agent lifecycle events. OpenLineage may matter if the WG addresses data provenance for RAG pipelines or tool outputs.

**References:**
- [cloudevents.io](https://cloudevents.io/)
- [openlineage.io](https://openlineage.io/)
- [OpenTelemetry eBPF instrumentation HTTP support](https://github.com/open-telemetry/opentelemetry-ebpf-instrumentation/tree/main/pkg/ebpf/common/http)
- [Harbor RFC: ATIF trajectory format](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md)

---

### 17. Academic Research

Several academic papers have surveyed or contributed to the agent observability space:

- **"AgentOps: Enabling Observability of LLM Agents"** (arXiv:2411.05285, Nov 2024) - Surveys 17 tools and identifies that existing tools focus on LLM metrics but lack observability for agent-specific artifacts (goals, plans, tool sequences). Key finding: none of the tools surveyed trace goals or plans as first-class artifacts.
- **"Beyond Task Completion: An Assessment Framework for Evaluating Agentic AI Systems"** (arXiv:2512.12791, Dec 2024) - Four evaluation pillars: LLM, Memory, Tools, Environment. Treats telemetry as the mechanism for interpretability and root cause analysis.
- **"Design Principles and Guidelines for LLM Observability"** (ACM CHI 2025) - Human-factors study of developer needs for LLM observability tools.
- **"Evaluation and Benchmarking of LLM Agents: A Survey"** (arXiv:2507.21504, KDD 2025) - Notes that enterprise requirements for audit/compliance traces are underserved.
- **["AgentTrace: A Structured Logging Framework for Agent System Observability"](https://arxiv.org/abs/2602.10133)** (arXiv:2602.10133, Feb 2026; unrelated to Cursor's Agent Trace spec despite the name overlap) - Frames observability as a security and accountability layer, capturing operational, cognitive, and contextual logs for agent runtime behavior.
- **["Governance-Aware Agent Telemetry for Closed-Loop Enforcement in Multi-Agent AI Systems"](https://arxiv.org/abs/2604.05119)** (arXiv:2604.05119, Apr 2026) - Proposes extending OTel with governance attributes, real-time OPA-compatible policy detection, an enforcement bus, and cryptographic provenance.

**Relevance to the working group:** The academic literature confirms that goal tracing, plan tracing, and audit-grade session records are gaps across the landscape. These findings should inform our use case prioritization.

---

### 18. A2A (Agent-to-Agent protocol) and agentgateway

[A2A](https://github.com/a2aproject/A2A) is the agent-to-agent interoperability protocol that joined AAIF as a hosted project in August 2026 (Google-launched April 2025; IBM's ACP merged August 2025; v1.0 March 2026). It standardizes agent discovery, task delegation, and exchange between agents across vendors. The agent card (`.well-known/agent-card.json`, RFC 8615) carries declared capabilities, auth requirements, and a signed identity.

[agentgateway](https://github.com/solo-io/agentgateway) (solo.io, joined AAIF June 2026) is a traffic mediation and control plane between agents and infrastructure, handling MCP and A2A traffic, with one-click deployment on AWS/Azure/GCP marketplaces.

**Observability relevance:** A2A is the inter-agent boundary the WG already tracks (protocol-aware tracing across MCP and A2A appears in OTel GenAI, AOS, and AGNTCY). Two observability-relevant properties stand out:

- **Signed agent cards create a verification surface.** A2A v1.0 signs cards, but identity verification of card claims against runtime behaviour is an open problem tracked in [a2aproject/A2A issue #1672](https://github.com/a2aproject/A2A/issues/1672). Signatures prove *who published* a card, not that the agent *behaves as declared*. This maps to the WG's "passive observability vs enforcement" tension: declared capabilities (card) vs observed capability use (trace) vs enforced policy (agentgateway boundary).
- **agentgateway is a natural enforcement point.** If declared-vs-observed reconciliation is the gap, the gateway boundary is where policy checks can compare requested actions against declared capabilities - the E2 layer in an evidence ladder (declared -> observed -> enforced -> corroborated -> anchored).

**Interaction opportunity:** Medium. The A2A issue tracker explicitly invites a standardized identity-verification mechanism. The WG's gap analysis could name this as an upstream contribution opportunity, and the "evidence layer" (who verifies declarations and can prove it later) is currently unclaimed across the hosted stack.

**Prior work relevant to this gap** (open-source, Apache-2.0, declared-vs-observed):

| Project | What it contributes to the landscape |
|---|---|
| `mcp-evidence-validator` (Empire Labs) | Declared-vs-observed checks for MCP servers with a tamper-evident SHA-256 ledger; roadmap includes A2A agent-card validation (v0.3) extending the same model to the agent-to-agent boundary |
| `mcp-governance-risks-framework` (Empire Labs) | Structured risk framework for MCP deployments - governance, trust-boundary, and supply-chain risk surfaces |
| `witnessos` (Empire Labs) | Public promotional repo for the evidence-grade compliance product; E0-E4 evidence grades + external anchoring (TSA timestamp, Merkle checkpoint) |
| OWASP Agent Observability Standard (AOS) | Instrumentation specs for A2A and MCP observability - complementary, protocol-level |

These are reference points, not a pitch: declared-vs-observed is a measurement method that composes with every layer of the stack without displacing any of them.

---

## Landscape Themes

### What's converging

1. **OTel as the wire protocol.** Nearly every effort either builds on OTel directly or provides OTel export. This is the clear consensus for runtime telemetry transport.

2. **Span-based agent tracing.** The span tree model (agent -> LLM call -> tool use) is the dominant paradigm. Most implementations agree on this basic structure.

3. **Protocol-aware agent tracing.** MCP and A2A have become recurring protocol surfaces across OTel GenAI, AOS, and AGNTCY. Observability standards increasingly need to describe not just model calls, but protocol boundaries and context propagation across them.

4. **Token/cost tracking.** Every effort includes token counts. Cost attribution is universally recognized as important.

### What's still fragmented

1. **Session models.** There is no consensus on how to model an agent session as a coherent unit - as opposed to a collection of individual spans. Long-running, multi-turn agent sessions are not well-served by span trees alone. Langfuse, LangSmith, and W&B Weave each have session concepts, but they're incompatible.

2. **Annotation and evaluation layers.** Post-hoc analysis (task segmentation, quality evaluation, failure classification) is done differently by every platform. No shared format exists for layering evaluative metadata on top of traces.

3. **Goal and plan tracing.** Academic research (arXiv:2411.05285) confirms that none of the 17 surveyed tools trace agent goals or plans as first-class artifacts. This is a gap across the entire landscape.

4. **Non-LLM agent behavior.** Most specs focus on LLM call instrumentation. Agent behaviors that don't involve LLM calls (file operations, process management, API calls, resource provisioning) are underspecified.

5. **Multi-agent coordination and inter-agent messaging.** The OTel #2664 proposal addresses this, but it's still at the proposal stage. When agent A hands off to agent B (via A2A, MCP, or other protocols), there is no standard for representing that handoff in a trace.

6. **Side effects and world-state changes.** What did the agent change in the world? Most specs track tool calls but don't model the observable impact of those calls as first-class data.

7. **Content capture at scale.** OTel span attributes have size limits. Full prompt/completion capture for debugging, replay, and evaluation requires approaches beyond standard OTel spans (events, logs, or complementary formats).

8. **Proxy vs. SDK architectural split.** Helicone's proxy approach (low coupling, universal compatibility, limited depth) vs. SDK-based tools (rich semantics, tighter coupling) represents an unresolved design tension. A standard should be implementable in both architectures.

9. **Passive observability vs. enforcement.** AOS and recent academic work push beyond "record what happened" toward instrumentable agents, policy hooks, and runtime intervention. The boundary between observability, control, and governance is not yet settled.

### Open questions for the working group

Based on the gaps above, several questions emerge for the working group to investigate:

1. **Is there a need for a session-level convention** that complements OTel's span-based telemetry? If so, should it be an OTel extension, a standalone format such as ATIF, or something else?

2. **How should evaluation and quality data relate to traces?** Is there value in standardizing how post-hoc analysis (task labels, quality scores, failure classifications) is layered on top of observability data?

3. **How do code attribution and behavioral observability relate?** Agent Trace covers "who wrote this code" - is there value in defining how that connects to runtime agent behavior data?

4. **What guidance is needed for content capture?** Full prompt/completion content is essential for many use cases but doesn't fit neatly into OTel span attributes. What approaches should the community consider?

5. **Span trees or event streams?** The dominant model in the landscape is OTel-style span trees - hierarchical parent-child relationships with start/end times. But agent sessions are inherently sequential and incremental: a stream of turns, tool calls, and responses that unfold over time. Some approaches (OWASP AOS's turn/step model, CloudEvents-style event envelopes) lean toward event-stream semantics. Is the span tree the right primitive for agent observability, or does the community need an event-stream model - or both? What are the trade-offs for different use cases (real-time monitoring vs. post-hoc analysis vs. replay)?

6. **Are coding agents the right starting point, or should we generalize?** Much of the existing work focuses on coding agents. What do DevOps agents, monitoring agents, and autonomous agents need differently?

7. **Where does runtime intervention belong?** If agent observability is used for hard controls, policy enforcement, or human approval gates, should those hooks be part of the same standard as traces, or a separate control-plane specification linked by shared identifiers?

---

## How to contribute to this document

This survey is maintained by the Observability Working Group. To suggest additions or corrections:
- Open a discussion in the working group channel
- Propose edits with context on what changed and why

We aim to keep this document current as the landscape evolves.
