# Use Cases for Agent Observability

**AAIF Observability Working Group**
**Date:** 2026-03-15
**Status:** Living document - last reviewed 2026-08-13; contributions welcome

---

## Purpose

This document catalogs use cases for agent observability across the AAIF community. It is intentionally broad - we want to capture the full range of reasons people need visibility into agent behavior, not just the ones any single organization cares about.

**This is a living document.** Working group members are encouraged to add use cases, refine existing ones, or note which use cases are most important to their organization. The goal is to build a shared understanding of what we're collectively trying to enable.

---

## How to read this document

Each use case follows a consistent structure:
- **Description:** What the practitioner needs to do
- **Target audience:** Which roles or organizations need this
- **What data is required:** What the observability layer must capture to support this
- **Current state:** How well existing tools/specs address this today

### Cross-cutting telemetry requirements

The following requirements apply across the use cases and are not repeated in every entry:

- **Source and trust:** Telemetry should identify its producer and observation point, distinguishing agent self-reporting from framework, gateway, identity-provider, sandbox, operating-system, network, or security-sensor evidence. Where integrity matters, records should indicate available signing, attestation, or tamper-evidence mechanisms without implying that these prove completeness or truthfulness.
- **Privacy and governance:** Content, identity, and correlation fields should carry enough policy metadata to enforce minimization, sensitivity classification, redaction, consent, access control, residency, retention, and deletion requirements. Raw credentials and secrets must not be captured.
- **Completeness and sampling:** Records should declare applicable sampling decisions, dropped-event counts, collection gaps, and completeness requirements. Audit-required events must be distinguishable from telemetry that may be sampled or discarded.
- **Schema evolution:** Telemetry should identify the schema, semantic-convention, instrumentation, agent, model, tool, and configuration versions needed to interpret historical records and compare behavior over time.
- **Correlation and causality:** Implementations should provide stable identifiers and causal links across sessions, tasks, messages, delegations, tools, and artifacts. Ordering must not depend only on wall-clock timestamps or a single parent-child span tree, especially for concurrent, queued, suspended, or resumed work.

---

## Use Case Categories

### A. Debugging and Root Cause Analysis

#### A1. Why did the agent do that?

**Description:** An agent produced an unexpected output, took a wrong path, or failed to complete a task. The practitioner needs to reconstruct the observable decision context and action sequence - what information was available, which steps occurred, and what explicit plans or decision summaries guided them.

**Target audience:** Developers building agent systems, SREs debugging production incidents, QA engineers investigating test failures.

**What data is required:** Conversation history (prompts and completions, subject to capture policy), tool call inputs/outputs, explicit plans or decision summaries emitted by the agent, and the effective context or context-manifest metadata at each decision point. Private chain-of-thought is not required.

**Current state:** LangSmith and Arize Phoenix provide good trace-level debugging for LLM calls. Gap: reconstructing the full session-level decision stream (not just individual calls) and understanding context management decisions (what was in the window, what was dropped).

#### A2. Where did the agent get stuck?

**Description:** An agent spent excessive time or tokens on a subtask, entered a retry loop, or repeatedly attempted failing approaches. The practitioner needs to identify bottlenecks and inefficient patterns.

**Target audience:** Developers optimizing agent performance, platform teams managing agent compute costs.

**What data is required:** Timing data per step, token usage per turn, tool call success/failure rates, detection of repeated patterns (same tool called with similar inputs), context compaction events.

**Current state:** OTel spans provide latency data. Token counts are tracked by most tools. Gap: pattern detection (retry loops, repeated failures) requires session-level analysis, not just span inspection.

#### A3. Reproducing agent behavior

**Description:** A practitioner needs to reproduce a specific agent session - either to debug an issue, validate a fix, or create a test case. This requires enough data to replay the session or set up equivalent conditions.

**Target audience:** Developers, QA engineers, researchers studying agent behavior.

**What data is required:** Complete session trajectory including inputs, model outputs, tool results, model and agent configuration versions, and relevant environmental state or snapshots. This should support controlled replay or reconstruction; exact reproduction may remain impossible because of model and environment non-determinism.

**Current state:** Most platforms capture enough for approximate replay. Gap: no standard format for session capture that enables cross-tool replay.

---

### B. Cost Management and Optimization

#### B1. How much did this agent session cost?

**Description:** A practitioner needs to know the total cost of an agent session - including LLM API costs, tool execution costs, and compute costs - broken down by subtask.

**Target audience:** Engineering managers, platform teams, finance teams, anyone with an AI budget.

**What data is required:** Token usage (input, output, cached, reasoning) per model call, model pricing data, tool execution duration and resource consumption, session-level aggregation.

**Current state:** Token counts are widely tracked. Gap: cost attribution to subtasks (not just total session cost), standardized cost modeling across providers, non-LLM costs (tool execution, compute).

#### B2. What's the cost per successful outcome?

**Description:** Beyond per-session cost, practitioners need to understand the cost efficiency of their agent systems - how much does it cost to successfully complete a task, and how does that vary by task type, model, or configuration?

**Target audience:** Engineering leadership, product managers deciding whether agent automation is worth the cost.

**What data is required:** Session costs (B1) linked to task outcomes (success/failure/partial), task type classification, model and configuration metadata. Requires both cost data and outcome evaluation.

**Current state:** Individual tools provide pieces of this. Gap: no standard way to link cost data to outcome labels across tools.

#### B3. Where is the waste?

**Description:** Identifying sessions or patterns where agents spend tokens without making progress - retry loops, exploration dead ends, unnecessary tool calls, context that gets compacted away.

**Target audience:** Platform teams optimizing agent systems, developers improving agent prompts and configurations.

**What data is required:** Turn-level token usage, tool call outcomes, detection of repeated/failed patterns, context compaction events and what was lost.

**Current state:** Requires session-level analysis that most span-based tools don't provide natively. Understanding waste patterns requires looking at the session as a whole, not just individual spans.

---

### C. Code Attribution and Provenance

#### C1. Which code was written by AI?

**Description:** Understanding what portion of a codebase was generated by AI agents, which models were involved, and which human sessions produced the code.

**Target audience:** Engineering managers, security teams, compliance teams, code reviewers.

**What data is required:** File-level and line-level attribution of AI vs. human authorship, model identifiers, session/conversation IDs linking code to the agent interaction that produced it.

**Current state:** Agent Trace (Cursor) directly addresses this with a focused spec. Adopted by multiple coding tools. Gap: no link between the code attribution data and the behavioral data about how the agent decided to write that code.

#### C2. Security review of AI-generated code

**Description:** When a vulnerability is found in AI-generated code, the security team needs to identify all other code produced in the same session or by the same model configuration, to scope the review.

**Target audience:** Security teams, compliance officers.

**What data is required:** Code attribution (C1) linked to session data, model configuration, and ideally the full conversation context. The ability to query "show me all code from sessions where the agent also produced this vulnerable pattern."

**Current state:** Agent Trace provides the attribution layer. Gap: linking attribution to session behavior requires a bridge between Agent Trace and agent observability data.

---

### D. Evaluation and Quality Assurance

#### D1. How well is the agent performing on this task type?

**Description:** Measuring agent performance across task categories - success rates, quality scores, time to completion - and tracking how performance changes over time or across configurations.

**Target audience:** Product managers, ML engineers, developers iterating on agent systems.

**What data is required:** Task outcome labels (success/failure/partial), quality scores (human or automated), task type classification, model and configuration metadata, temporal tracking.

**Current state:** Evaluation platforms (LangSmith, Phoenix, Braintrust) each have their own approaches. OTel GenAI defines [`gen_ai.evaluation.result` events](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md#event-gen_aievaluationresult) as relevant prior art for recording evaluation results alongside traces. Gap: no broadly adopted standard format for portable evaluation labels and results across tools.

#### D2. Regression detection

**Description:** Detecting when a model update, prompt change, or configuration change causes agent performance to degrade - before users notice.

**Target audience:** ML engineers, platform teams, anyone deploying agent systems to production.

**What data is required:** Baseline performance metrics linked to configuration, continuous evaluation data, alerting on metric changes.

**Current state:** Individual platforms provide this within their ecosystem. Gap: standardized metrics and thresholds that work across tools.

#### D3. Comparison across models/configurations

**Description:** A/B testing agent configurations - different models, prompts, tool sets, or architectures - and comparing outcomes on equivalent tasks. This includes metrics-driven development workflows where teams rerun benchmarks, simulations, or automated tests against candidate changes before production rollout.

**Target audience:** ML engineers, researchers, developers optimizing agent systems.

**What data is required:** Controlled experiment metadata, task-level outcomes, cost data, confidence or sample-size metadata where available, benchmark run identifiers, and configuration parameters.

**Current state:** Ad-hoc. Each team builds their own comparison infrastructure. Gap: no common way to represent benchmark reruns, A/B-style comparisons, low-confidence simulation results, and production outcome comparisons in one portable observability format.

---

### E. Safety and Compliance

#### E1. What actions did the agent take in the world?

**Description:** Understanding the observable side effects of an agent session - files created/modified/deleted, APIs called, resources provisioned, processes started/stopped, messages sent.

**Target audience:** Security teams, compliance officers, SREs, anyone responsible for the blast radius of agent actions.

**What data is required:** Tool call inputs and outputs with enough detail to understand the real-world impact. Not just "the agent called the file_write tool" but "the agent wrote to /etc/nginx/nginx.conf and reloaded nginx."

**Current state:** Tool call tracing captures inputs/outputs. Gap: modeling the side effects (world-state changes) as first-class data rather than requiring consumers to parse tool outputs. For security, safety, and compliance, agent-produced telemetry may not be sufficient; sandbox, gateway, operating-system, network, or environment-derived telemetry may be needed as a more trustworthy source of world-state changes.

#### E2. Did the agent exceed its authorized scope?

**Description:** Detecting when an agent accessed resources, called tools, or took actions outside its intended scope - either in real-time (for prevention) or after the fact (for audit).

**Target audience:** Security teams, compliance officers, platform teams managing agent permissions.

**What data is required:** Complete record of all tool calls, permission decisions (what was requested vs. what was granted), policy metadata (what the agent was authorized to do).

**Current state:** Most agent frameworks have permission systems, but conventions for logging permission decisions alongside agent traces are inconsistent. [OCSF 1.9](https://schema.ocsf.io/1.9.0/) provides relevant AI Operation, actor, authorization, and delegation structures for security events. Gap: practical mappings between those events, agent-framework permission models, and OTel traces.

#### E3. Audit trail for regulated environments

**Description:** Producing a tamper-evident, complete record of agent actions for regulatory compliance - who initiated the session, what the agent did, what it changed, and who approved each action.

**Target audience:** Compliance teams in regulated industries (finance, healthcare, government), legal teams.

**What data is required:** Append-only or tamper-evident session records, user and agent identity, delegation-of-authority records, approval chains, human-in-the-loop checkpoints, policy-check outcomes, complete action logs, timestamps, data lineage, telemetry-source metadata, and explicit sampling or collection-gap indicators. Retention and access controls must support applicable audit-log requirements such as [EU AI Act Article 12](https://artificialintelligenceact.eu/article/12/).

**Current state:** Teams in regulated industries still assemble bespoke solutions. [OCSF 1.9](https://schema.ocsf.io/1.9.0/) provides AI-specific event, delegation, and record-integrity structures, while OTel provides execution traces. Gap: a broadly adopted profile that combines complete agent-action coverage, approvals, trustworthy collection, retention, and trace correlation for audit use.

---

### F. Multi-Agent Systems

#### F1. Tracing across agent boundaries

**Description:** When agents delegate work to sub-agents, orchestrate teams of agents, or communicate via shared context, practitioners need end-to-end visibility across the full agent graph.

**Target audience:** Developers building multi-agent systems, platform teams operating them.

**What data is required:** Session-to-session linking (parent/child relationships), shared context tracking, delegation metadata (why this sub-agent was invoked, what it was asked to do).

**Current state:** OTel distributed tracing provides the basic propagation model, and the OTel #2664 proposal addresses agent teams. The experimental [A2A traceability extension](https://github.com/a2aproject/a2a-samples/blob/main/extensions/traceability/v1/spec.md) can return a custom nested agent/tool trace in message or artifact metadata, but it does not define W3C Trace Context propagation. Gap: practical propagation and correlation conventions that work across agent protocols and frameworks.

#### F2. Understanding agent-to-agent communication

**Description:** When agents communicate (via tool calls, shared memory, message passing), practitioners need to understand what was communicated, whether it was understood correctly, and how it influenced downstream behavior.

**Target audience:** Developers debugging multi-agent interactions, researchers studying emergent agent behavior.

**What data is required:** Inter-agent message content, shared state changes, causal links between agent actions.

**Current state:** Largely unaddressed by existing specs. The OTel #2664 proposal's "team" concept is a starting point. The experimental [A2A traceability extension](https://github.com/a2aproject/a2a-samples/blob/main/extensions/traceability/v1/spec.md) exposes nested invocation details, but does not standardize message meaning, causal influence, authenticated identity, or delegated authority.

---

### G. Operational Monitoring

#### G1. Real-time agent health

**Description:** Monitoring running agent systems for health indicators - latency, error rates, token consumption rates, tool failure rates - and alerting when things go wrong.

**Target audience:** SREs, platform teams, on-call engineers.

**What data is required:** Metrics (not just traces) - aggregated token usage rates, error rates by tool/model, latency percentiles, active session counts.

**Current state:** OTel metrics provide the foundation. GenAI semantic conventions define relevant metrics. Gap: agent-specific health indicators (e.g., "agent is in a retry loop" or "context window is critically full") aren't standardized.

#### G2. Capacity planning

**Description:** Predicting future resource needs (API rate limits, compute, cost) based on historical agent usage patterns.

**Target audience:** Platform teams, finance teams, infrastructure teams.

**What data is required:** Historical usage data with enough granularity to model trends by task type, user segment, and time of day.

**Current state:** Each platform provides its own usage analytics. No standard for agent usage data that enables cross-platform capacity planning.

---

### H. Research and Improvement

#### H1. Discovering new failure modes

**Description:** Beyond known failure categories, practitioners need to discover unknown failure patterns - the "unknown unknowns" of agent behavior.

**Target audience:** ML researchers, agent developers trying to improve systems, red teams.

**What data is required:** Rich session data, including content where policy permits, that can be analyzed with open-ended methods (LLM-based analysis, clustering, manual review). This requires more than structured metrics, plus sensitivity labels, redaction state, access controls, and retention metadata for the behavioral record.

**Current state:** Requires access to full session data, which most tracing tools capture but don't expose in a format designed for this kind of analysis.

#### H2. Training and fine-tuning data

**Description:** Using agent session recordings as training data - for fine-tuning models, training reward models, or building datasets for offline RL.

**Target audience:** ML engineers, researchers.

**What data is required:** Complete input/output pairs with quality labels, tool use patterns with outcomes, human feedback signals. The format must be convertible to training data formats.

**Current state:** No standard session format designed with training data extraction as a use case. Teams build bespoke pipelines. [ATIF](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md) is relevant prior art for an interchangeable session-level trajectory format that could be derived from traces for training and evaluation workflows.

#### H3. Benchmarking across implementations

**Description:** Comparing agent performance across different implementations, frameworks, or providers on equivalent tasks.

**Target audience:** Researchers, teams evaluating agent frameworks, the broader AI community.

**What data is required:** Standardized task definitions, outcome measurements, cost data, and trajectory data - all in a common format that enables apples-to-apples comparison.

**Current state:** SWE-bench and similar benchmarks exist for specific domains, and projects such as [Exgentic](https://github.com/Exgentic/exgentic/) are relevant implementation references for cross-implementation benchmarking. Gap: no standard observability format that makes benchmark results comparable across implementations.

---

## Contributing

This document is maintained by the Observability Working Group. To add a use case:

1. Choose the appropriate category (A-H) or propose a new one
2. Follow the template: Description, Target audience, What data is required, Current state
3. Submit via the working group's contribution process

When adding use cases, consider:
- Is this genuinely distinct from an existing use case, or a variant of one?
- Can you name a real scenario where this need arose?
- What data would be required that isn't already covered by other use cases?

---

## Appendix: Use Case Priority Matrix

*To be filled in by working group members. Each organization can indicate which use cases are highest priority for them, helping the working group focus on the most broadly needed capabilities first.*

| Use Case | Priority (Your Org) | Notes |
|----------|---------------------|-------|
| A1. Why did the agent do that? | | |
| A2. Where did the agent get stuck? | | |
| A3. Reproducing agent behavior | | |
| B1. Session cost | | |
| B2. Cost per outcome | | |
| B3. Where is the waste? | | |
| C1. Code attribution | | |
| C2. Security review | | |
| D1. Task performance | | |
| D2. Regression detection | | |
| D3. Model comparison | | |
| E1. Agent side effects | | |
| E2. Scope enforcement | | |
| E3. Audit trail | | |
| F1. Multi-agent tracing | | |
| F2. Agent communication | | |
| G1. Real-time health | | |
| G2. Capacity planning | | |
| H1. Failure discovery | | |
| H2. Training data | | |
| H3. Benchmarking | | |
