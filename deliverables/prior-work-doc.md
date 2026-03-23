# Prior Work in Agent Observability

**AAIF Observability Working Group - Landscape Survey**  
**Date:** 2026-03-15  
**Status:** Living document - last updated 2026-03-23

---

## Purpose

This document surveys the existing proposals, specifications, and implementations related to agent observability. The goal is to give working group members a shared understanding of what exists today, how mature each effort is, and where there are opportunities for collaboration or extension.

This is not a competitive ranking - many of these efforts address different facets of the same problem space. We include them all because the working group should be aware of the full landscape.

**Versioning note:** References to OpenTelemetry GenAI semantic conventions in this document are based on the development-state semantic conventions active as of **2026-03-23**. The GenAI SIG's conventions are evolving rapidly, so the specific coverage and gaps identified here may shift as the OTel spec evolves.

---

## Summary Table

| Initiative | Scope | Maturity | Open/Proprietary | Key Strength |
|---|---|---|---|---|
| OTel GenAI Semantic Conventions | LLM + agent span attributes | Experimental (Development) | Open (Apache 2.0) | Broad industry backing, existing OTel ecosystem |
| OTel GenAI SIG - Agentic Systems Proposal | Tasks, actions, teams, memory | Proposal (Issue #2664) | Open | Multi-agent modeling |
| Agent Trace (Cursor) | AI code attribution | Draft RFC (v0.1.0) | Open (CC BY 4.0) | Coding tool adoption, simplicity |
| OWASP Agent Observability Standard (AOS) | Security-focused agent tracing | Early draft | Open | Security and compliance framing |
| OpenInference (Arize) | LLM/RAG span instrumentation | Production use | Open (Apache 2.0) | Practical, OTel-compatible |
| OpenLLMetry (Traceloop) | LLM provider instrumentation | Production use | Open (Apache 2.0) | Broad provider coverage |
| LangSmith (LangChain) | Full-stack LLM observability | Production | Proprietary (OTel export) | Deep LangChain integration |
| Arize Phoenix | LLM/agent observability platform | Production | Open (self-hostable) | End-to-end: tracing + eval |
| MLflow Tracing | LLM/agent tracing in ML platform | Production | Open (Apache 2.0) | 30M+ monthly downloads, Databricks ecosystem |
| W&B Weave | LLM observability + RL trajectories | Production | SDK open / backend proprietary | Unified MLOps + LLMOps |
| Langfuse | LLM observability with published data model | Production | Open source | OTel-native, session-aware, self-hostable |
| Helicone | Proxy-based LLM observability | Production | Open source | Zero-SDK integration, 2B+ interactions |
| Monocle (LF AI & Data) | GenAI auto-instrumentation framework | Early (v0.7.6) | Open (Apache 2.0) | Broadest framework auto-instrumentation |
| AGNTCY | Multi-agent interop + observability | Early-stage | Open (Apache 2.0) | Cross-agent context propagation |
| OpenLIT | OTel-native LLM observability | Production | Open | Follows OTel semconv closely |

---

## Coverage Comparison Matrix

This matrix is intentionally directional rather than exhaustive. The columns are aligned to the AAIF charter's scope areas rather than generic tracing primitives, so the gaps shown here more directly answer where this working group may need to adopt, extend, or define standards.

| Initiative | Multi-Agent Flows | Protocol Observability | Cross-Boundary Context | Agent Side Effects | Memory / Context | Reasoning / Decision Traces | Feedback / Eval Hooks | Multi-Modal | Operational Metrics |
|---|---|---|---|---|---|---|---|---|---|
| OTel GenAI Semantic Conventions | Partial | Partial | Partial | Partial | Partial | No | Partial | Partial | Yes |
| OTel Agentic Systems Proposal | Yes | No | Partial | Partial | Yes | Partial | No | No | Partial |
| Agent Trace (Cursor) | No | No | No | No | No | No | No | No | No |
| OWASP AOS | Partial | Partial | Partial | Partial | Partial | No | Partial | No | Partial |
| OpenInference | No | No | No | No | Partial | No | No | No | Partial |
| OpenLLMetry | No | No | No | No | No | No | No | No | Partial |
| LangSmith | Partial | No | No | Partial | Partial | Partial | Yes | Partial | Yes |
| Arize Phoenix | Partial | No | No | Partial | Partial | Partial | Yes | Partial | Yes |
| MLflow Tracing | Partial | No | Partial | Partial | Partial | Partial | Yes | Partial | Yes |
| W&B Weave | Partial | No | No | No | Partial | Partial | Yes | Partial | Partial |
| Langfuse | Partial | No | No | No | Partial | Partial | Yes | Partial | Yes |
| Helicone | No | No | No | No | No | No | Partial | No | Yes |
| Monocle | Partial | No | No | Partial | Partial | No | No | Partial | Partial |
| AGNTCY | Yes | Partial | Yes | Partial | Partial | Partial | No | No | Yes |
| OpenLIT | No | No | No | No | No | No | No | No | Yes |

**Headline takeaway:** the ecosystem has reasonable coverage for operational metrics and some emerging coverage for multi-agent flows, but the AAIF charter areas with the largest whitespace are cross-boundary trace context, agent side effects, memory/context reproducibility, and reasoning/decision trace conventions. Protocol observability and evaluation hooks now have at least partial coverage in OpenTelemetry, but remain fragmented and incomplete.

---

## Detailed Assessments

### 1. OpenTelemetry GenAI Semantic Conventions

**What it is:** The OpenTelemetry project's official semantic conventions for generative AI systems - defining standard attribute names, span structures, and metric conventions for LLM calls, agent invocations, and tool use.

**Scope:**

- GenAI client spans (LLM calls): model name, token usage, temperature, prompts/completions
- Agent spans: `invoke_agent`, `create_agent` operations with span kind guidance (`CLIENT` for remote agents, `INTERNAL` for in-process)
- Tool use: typed as extension, function, or datastore
- Three signal types: traces, metrics, and events

**Maturity:** The GenAI semantic conventions are in Development status (not yet stable). Instrumentations using v1.36.0 or prior should not change their emitted convention version by default. The conventions are actively evolving.

**Key contributors:** Engineers from Amazon, Elastic, Google, IBM, Langtrace, Microsoft, OpenLIT, Scorecard, Traceloop, and others. Microsoft and Cisco (Outshift) have been particularly active in enhancing multi-agent observability conventions based on W3C Trace Context.

**Strengths:**

- Broadest industry coalition of any effort in this space
- Built on the proven OTel distributed tracing model
- Natural home for standardization - OTel is already the de facto standard for application observability
- Three-signal approach (traces, metrics, events) is more comprehensive than trace-only efforts
- Already covers more than basic LLM spans: agent invocation, tool execution, retrieval, multimodal output types, conversation correlation, and opt-in content capture

**Gaps (from the working group's perspective):**

- Full content capture is supported on an opt-in basis, but production use remains difficult because of privacy requirements, telemetry volume, backend size limits, and the lack of a standard way to reference externally stored content
- The current conventions are trace-first and span-centric, which works well for request-response and distributed execution but does not yet provide a strong session, trajectory, or graph model for long-running agent workflows
- Conversation correlation exists, but there is still no standard turn-level or step-level structure for modeling multi-turn decision streams, branching, or backtracking
- OpenTelemetry now includes a basic GenAI evaluation event, but it does not yet define a richer portable model for experiments, datasets, replay, judge configuration, or post-hoc analysis workflows
- Token usage is standardized, but normalized cost, billing, and organizational chargeback semantics are not
- Tool execution can be traced, but the observable side effects of agent actions are still under-modeled; there is no common taxonomy for outcomes such as state mutation, resource creation, notifications, or approvals

**Interaction opportunity:** High. OTel is the natural venue for runtime telemetry conventions, and it has already made meaningful progress beyond basic LLM spans. The working group should engage directly with the GenAI SIG on the next layer of standardization: session and turn semantics, external content references, side-effect modeling, and portable cost and evaluation metadata.

**References:**

- GenAI Semantic Conventions Overview
- Agent Spans Spec
- AI Agent Observability Blog Post

### 2. OTel Agentic Systems Proposal (Issue #2664)

**What it is:** A proposal within the OTel semantic conventions repo to define conventions for observability of generative AI agentic systems - going beyond individual LLM calls to model the higher-level structures of agent workflows.

**Scope:** Defines attributes for:

- Tasks - minimal trackable units of work, decomposable into subtasks
- Actions - how tasks are carried out (tool calls, LLM queries, API requests, vector DB queries, human input, workflows)
- Agents - the entities executing tasks
- Teams - dynamic groups of agents collaborating toward shared goals
- Artifacts - outputs produced by agent work
- Memory - persistent and scoped storage of knowledge and context

**Maturity:** Proposal stage (open GitHub issue). Not yet merged into the semantic conventions.

**Strengths:**

- Addresses the multi-agent coordination problem that simpler specs ignore
- Models memory and artifacts as first-class concepts
- Explicitly designed for complex, multi-step AI workflows

**Gaps:**

- Still at the proposal stage - significant design work remains
- The task/action decomposition may be too opinionated for some agent architectures
- No reference implementation yet

**Interaction opportunity:** High. This proposal is actively seeking input. Working group members building multi-agent systems should review and contribute.

**Reference:** GitHub Issue #2664

### 3. Agent Trace (Cursor)

**What it is:** An open specification for tracking AI-generated code, published by Cursor in January 2026. It defines a vendor-neutral JSON format for recording which code was written by humans vs. AI, at file and line granularity.

**Scope:** Code attribution only - which model produced which lines of code, in which session, at which time. The spec is intentionally narrow:

- Trace records with version, ID, timestamp, and file-level attribution
- Model identifiers following the models.dev convention (`provider/model-name`)
- Extensible metadata using reverse-domain notation for vendor-specific data
- Storage-agnostic (local files, git notes, databases - implementation decides)

**What it explicitly does not cover:**

- Legal ownership or copyright
- Training data provenance
- Code quality evaluation
- The agent's decision process, failed attempts, or cost

**Maturity:** Draft RFC (v0.1.0). Reference implementation in TypeScript. 637 GitHub stars, 50 forks, 18 open issues as of March 2026.

**Partners:** Amp, Amplitude, Cline, Cloudflare, Cognition, git-ai, Jules (Google), OpenCode, Tapes, Vercel. This is a strong coalition of coding tool vendors.

**Strengths:**

- Clear, narrow scope that's easy to implement
- Strong adoption among coding-focused AI tools
- Practical and immediately useful for code review and compliance workflows
- The "who wrote this code?" question has clear business value

**Gaps (from the working group's perspective):**

- Captures only the output (code attribution) - not the process (agent reasoning, tool use, cost, failed attempts)
- Limited to code-producing agents - doesn't generalize to DevOps agents, monitoring agents, or other non-coding agent types
- No concept of agent sessions, turns, or decision streams
- No support for non-code side effects (API calls, resource creation, process management)

**Interaction opportunity:** Medium. Agent Trace and broader agent observability are complementary - Agent Trace answers "who wrote this code?" while agent observability answers "how did the agent decide to write it, what did it cost, and what else did it do?" A working group deliverable could define how these layers relate. Agent Trace records could be a derived view of richer session data. The Cursor team has indicated openness to working with outside contributors to be a part of an advisory board or committee of maintainers - worth following up on.

**References:**

- agent-trace.dev
- GitHub: cursor/agent-trace
- InfoQ coverage

### 4. OWASP Agent Observability Standard (AOS)

**What it is:** An OWASP project defining an observability standard for AI agents with a security and compliance focus. It extends OpenTelemetry with agent-specific conventions.

**Maturity:** Early draft. The project has published initial spec documents including guidance on extending OTel for agent tracing.

**Strengths:**

- Security-first framing fills a gap that other specs don't address directly
- Built on OTel rather than inventing a new protocol
- OWASP's brand brings credibility in the security community

**Gaps:**

- Very early stage - limited adoption and community size
- Security focus may limit appeal for teams whose primary concern is performance/cost optimization

**Interaction opportunity:** Medium-high. Security and compliance are important use cases for agent observability. The working group should ensure our use case inventory covers the security/compliance angle, and OWASP AOS is a natural ally there. At the same time, it does feel that this may be more directly at the intersection of our WG's interaction with the Security WG - so perhaps better to wait.

**Reference:** aos.owasp.org

### 5. OpenInference (Arize)

**What it is:** An open specification from Arize AI for OTel-compatible instrumentation of LLM and AI applications. It defines span attributes and conventions specifically for LLM calls, retrieval operations, and tool use.

**Maturity:** Production use. Actively maintained, used by Arize Phoenix and integrated with multiple frameworks (LangChain, LlamaIndex, DSPy, OpenAI Agents SDK, etc.).

**Strengths:**

- Battle-tested in production observability workflows
- Covers the RAG pipeline well (retrieval spans, embedding spans, reranking)
- OTel-compatible - emits standard OTLP data
- Auto-instrumentors for popular frameworks reduce integration effort

**Gaps:**

- Focused on LLM application observability rather than autonomous agent behavior
- No session/trajectory model - individual calls, not decision streams
- Spec is maintained by a single vendor (Arize), though it's open source

**Interaction opportunity:** Medium. OpenInference demonstrates practical conventions that work. The working group can learn from what's been battle-tested here, even if the scope is narrower than what we're defining.

**Reference:** GitHub: Arize-ai/openinference

### 6. OpenLLMetry (Traceloop)

**What it is:** An open-source extension to OpenTelemetry providing instrumentation libraries for LLM providers (OpenAI, Anthropic, Cohere, etc.) and vector databases (Pinecone, Chroma, Qdrant, Weaviate). Available in Python and TypeScript.

**Maturity:** Production use. Integrates with Datadog, New Relic, Sentry, Honeycomb, and other backends.

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

- GitHub: traceloop/openllmetry
- openllmetry.org

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

**Reference:** langchain.com/langsmith

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
- No formal session/trajectory specification

**Interaction opportunity:** Low-medium. Phoenix is a consumer of whatever standards emerge, not a standards body. But it demonstrates what practitioners need from agent observability tooling.

**Reference:** phoenix.arize.com

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

**Reference:** MLflow Tracing Docs

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

**Reference:** Weave Docs

### 11. Langfuse

**What it is:** Open-source LLM observability platform with a published data model. OTel-native. Postgres + ClickHouse backend. Often cited as the leading open-source alternative to LangSmith.

**Maturity:** Production use. YC W23. Published data model with sessions, traces, observations (spans/generations/events), and scores.

**Strengths:**

- Open source with a published, documented data model
- OTel-native integration (both ingest and export)
- Session concept as a first-class grouping mechanism
- Self-hostable with standard infrastructure (Postgres + ClickHouse)

**Gaps:**

- Session model is simpler than what may be needed for complex agent workflows
- No agent-specific span taxonomy (compared to OpenInference)

**Interaction opportunity:** Medium. Langfuse's published data model is a good reference for what a practical session-aware trace model looks like. Their OTel integration approach is worth studying.

**Reference:** Langfuse Data Model

### 12. Emerging Startups (AgentOps, HoneyHive, Helicone)

These represent the startup wave in agent observability. Each has a distinct angle:

- AgentOps - Agent-first observability with time-travel debugging and session replay. Supports 400+ LLMs. Notable feature: saved completions for fine-tuning. Python-only, cloud-only.
- HoneyHive - Enterprise focus with human-in-the-loop evaluation. SOC 2, HIPAA, GDPR compliance. OTel-based tracing. Closed source, enterprise pricing.
- Helicone - Proxy-based approach (URL change, no SDK). Open source (YC W23). Built on Cloudflare Workers + ClickHouse + Kafka. 2B+ LLM interactions processed. Built-in caching is unique. Very low overhead (50-80ms).

**Architectural note:** Helicone's proxy approach vs. AgentOps/HoneyHive's SDK approach represents a real design tension - proxy gives low coupling and universal compatibility but limited depth; SDK gives rich semantics but tighter coupling.

**Interaction opportunity:** Low individually, but collectively they demonstrate the market's demand for agent observability and the diversity of approaches being tried.

### 13. Microsoft VS Code - Native OTel for Agent Observability

**What it is:** A proposal (GitHub Issue #293225) for native OpenTelemetry instrumentation in VS Code's Copilot Chat - instrumenting the agent runtime and tool execution directly with OTel GenAI conventions and emitting OTLP.

**Targets:** Run/session root span, tool-call spans, and LLM request spans/events (model, latency, tokens, cache).

**Maturity:** Proposal stage.

**Interaction opportunity:** Medium. Microsoft is a major player and their approach to agent observability in Copilot will influence the ecosystem. Worth tracking.

**Reference:** microsoft/vscode#293225

### 14. Monocle (LF AI & Data)

**What it is:** A community-driven open-source framework for auto-instrumenting GenAI and agentic applications. Monocle wraps popular frameworks (LangGraph, LlamaIndex, CrewAI, Google ADK, OpenAI Agent SDK, AWS Strands, Microsoft Agent Framework) with automatic instrumentation, capturing spans for inference calls, retrieval operations, tool invocations, and workflow steps - without requiring developers to write custom OTel code.

**Maturity:** LF AI & Data Sandbox project (accepted August 2024). Current version 0.7.6 (February 2026). Pre-1.0, but rapidly gaining framework coverage. A separate monocle-specs repo defines the GenAI metamodel.

**Relationship to OTel:** OTel-adjacent. Emits spans in an OTel-compatible format and works with OTel collectors, but the core value is a GenAI-specific metamodel that abstracts away the need for developers to manually implement OTel GenAI conventions. Not trying to replace OTel - it's a ready-made instrumentation layer that outputs to OTel.

**Strengths:**

- Broadest framework auto-instrumentation coverage of any single project
- Includes a GenAI test tool for validating expected agent/tool call behavior against captured traces
- LF AI & Data governance provides vendor neutrality

**Gaps:**

- Pre-1.0, sandbox stage
- Metamodel is Monocle-specific - not yet aligned with OTel GenAI semconv

**Interaction opportunity:** Medium-high. Monocle operates in the same foundation ecosystem (Linux Foundation) and is directly focused on the instrumentation problem. The metamodel in monocle-specs is worth reviewing for conventions the WG could adopt or influence.

**References:**

- GitHub: monocle2ai/monocle
- Metamodel specs
- LF AI & Data announcement

### 15. AGNTCY

**What it is:** An open infrastructure project for multi-agent interoperability, originally open-sourced by Cisco (March 2025), then donated to the Linux Foundation (July 2025). Describes itself as building the "Internet of Agents" - shared infrastructure so AI agents built by different vendors can discover, communicate with, and trust each other.

**Scope:** Six components: OASF (agent schema), Agent Directory (decentralized discovery), SLIM (secure messaging), Observe SDK (OTel-based tracing), Identity (decentralized agent identity), and Security (auth and encryption).

**Observability scope specifically:** The Observe SDK is an OTel extension with multi-agent-specific semantic conventions. Key capabilities:

- Framework-agnostic OTel-compliant instrumentation via decorators or native OTel primitives
- Cross-agent context propagation to reconstruct end-to-end traces spanning multiple autonomous agents
- Multi-agent-specific metrics: collaboration success rate, response time, task delegation accuracy
- Schema translation layer to normalize telemetry from heterogeneous OTel-compliant SDKs

**Maturity:** Early-stage (post-March 2025). 75+ supporting organizations including Cisco, Dell, Google Cloud, Oracle, Red Hat.

**Strengths:**

- Observability is one of six explicit pillars, not an afterthought
- Addresses the hardest part of multi-agent observability: cross-boundary context propagation
- LF governance and strong backer list

**Gaps:**

- Sub-1.0, still evolving rapidly
- Observe SDK adoption is nascent

**Interaction opportunity:** High. AGNTCY is under the same Linux Foundation umbrella, observability is a core pillar, and the cross-agent tracing problem is one the WG should understand deeply. The Observe SDK's conventions should be reviewed alongside OTel GenAI SIG proposals.

**References:**

- agntcy.org
- Observe SDK docs
- LF announcement

### 16. Adjacent Standards (CloudEvents, OpenLineage)

These are not agent observability specifications, but they operate in adjacent layers that the WG should be aware of.

**CloudEvents (CNCF, Graduated):** A vendor-neutral envelope format for event data, standardizing how event metadata (source, type, subject, time, ID) is expressed and transported. Production-grade (v1.0.2), adopted by AWS EventBridge, Azure Event Grid, Google Eventarc, and others. Relevant to agent observability as a potential transport envelope for agent events in event-driven multi-agent architectures (for example, Kafka-based agent buses). No current effort to standardize AI agent-specific CloudEvents schemas.

**OpenLineage (LF AI & Data, Graduated):** An open standard for collecting lineage metadata about data pipeline runs. Defines Job, Run, and Dataset entities with extensible facets. Widely adopted for SQL/Spark/Airflow/dbt pipeline lineage. Relevant to agent observability because it tracks "what data did the agent's pipeline consume and produce" - the data layer beneath agent reasoning. The Run/Job/Dataset model maps interestingly onto agentic systems (workflow = Job, execution = Run, tool outputs = Datasets), but this mapping has not been formalized.

**Interaction opportunity:** Low for direct adoption, but worth tracking. CloudEvents may matter if the WG defines event-based conventions for agent lifecycle events. OpenLineage may matter if the WG addresses data provenance for RAG pipelines or tool outputs.

**References:**

- cloudevents.io
- openlineage.io

### 17. Academic Research

Several academic papers have surveyed or contributed to the agent observability space:

- "AgentOps: Enabling Observability of LLM Agents" (`arXiv:2411.05285`, Nov 2024) - Surveys 17 tools and identifies that existing tools focus on LLM metrics but lack observability for agent-specific artifacts (goals, plans, tool sequences). Key finding: none of the tools surveyed trace goals or plans as first-class artifacts.
- "Beyond Task Completion: An Assessment Framework for Evaluating Agentic AI Systems" (`arXiv:2512.12791`, Dec 2024) - Four evaluation pillars: LLM, Memory, Tools, Environment. Treats telemetry as the mechanism for interpretability and root cause analysis.
- "Design Principles and Guidelines for LLM Observability" (ACM CHI 2025) - Human-factors study of developer needs for LLM observability tools.
- "Evaluation and Benchmarking of LLM Agents: A Survey" (`arXiv:2507.21504`, KDD 2025) - Notes that enterprise requirements for audit/compliance traces are underserved.

**Relevance to the working group:** The academic literature confirms that goal tracing, plan tracing, and audit-grade session records are gaps across the landscape. These findings should inform our use case prioritization.

---

## Landscape Themes

### What's converging

**OTel as the wire protocol.** Nearly every effort either builds on OTel directly or provides OTel export. This is the clear consensus for runtime telemetry transport.

**Span-based agent tracing.** The span tree model (`agent -> LLM call -> tool use`) is the dominant paradigm. Most implementations agree on this basic structure.

**Token/cost tracking.** Every effort includes token counts. Cost attribution is universally recognized as important.

### What's still fragmented

**Session/trajectory models.** There is no consensus on how to model an agent session as a coherent unit - as opposed to a collection of individual spans. Long-running sessions, non-standard flow (for example, fork/backtrack patterns), context management, and multi-turn decision streams are not well-served by span trees alone.

**Annotation and evaluation layers.** Basic evaluation hooks are beginning to emerge in OpenTelemetry, but richer post-hoc analysis (segmentation, quality evaluation, failure classification, experiments, replay) is still done differently by every platform. No shared end-to-end format exists yet.

**Non-LLM agent behavior.** Most specs focus on LLM call instrumentation. Agent behaviors that don't involve LLM calls (file operations, process management, API calls, resource provisioning) are underspecified.

**Multi-agent coordination.** The OTel #2664 proposal addresses this, but it's still at the proposal stage. Production frameworks handle multi-agent tracing with ad-hoc solutions.

**Side effects and world-state changes.** What did the agent change in the world? Newer specs can trace tool calls, but they still do not model the observable impact of those calls as first-class data.

**Content capture at scale.** OTel now supports opt-in content capture and points toward externalized content handling, but full prompt/completion capture for debugging, replay, and evaluation still requires approaches beyond standard span attributes alone.

**Cross-boundary trace context.** Propagation of trace context across system boundaries remains a largely overlooked topic, and none of the existing initiatives address it comprehensively.

---

## Open Questions for the Working Group

Based on the gaps above, several questions emerge for the working group to investigate:

1. Is there a need for a session-level convention that complements OTel's span-based telemetry? If so, should it be an OTel extension, a standalone format, or something else?
2. How should evaluation and quality data relate to traces? Is there value in standardizing how post-hoc analysis (task labels, quality scores, failure classifications) is layered on top of observability data?
3. How do code attribution and behavioral observability relate? Agent Trace covers "who wrote this code" - is there value in defining how that connects to runtime agent behavior data?
4. What guidance is needed for content capture? Full prompt/completion content is essential for many use cases but doesn't fit neatly into OTel span attributes. What approaches should the community consider?
5. Span trees or event streams? The dominant model in the landscape is OTel-style span trees - hierarchical parent-child relationships with start/end times. But agent sessions are inherently sequential and incremental: a stream of turns, tool calls, and responses that unfold over time. Some approaches (OWASP AOS's turn/step model, CloudEvents-style event envelopes) lean toward event-stream semantics. Is the span tree the right primitive for agent observability, or does the community need an event-stream model - or both? What are the trade-offs for different use cases (real-time monitoring vs. post-hoc analysis vs. replay)?

---

## How to Contribute to This Document

This survey is maintained by the Observability Working Group. To suggest additions or corrections:

- Open a discussion in the working group Discord
- Propose edits with context on what changed and why

We aim to keep this document current as the landscape evolves.