# Use Cases for Agent Observability

**AAIF Observability Working Group**
**Date:** 2026-03-15
**Status:** Living document - last reviewed 2026-07-08; contributions welcome

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

---

## Use Case Categories

### A. Debugging and Root Cause Analysis

#### A1. Why did the agent do that?

**Description:** An agent produced an unexpected output, took a wrong path, or failed to complete a task. The practitioner needs to reconstruct the agent's decision process - what it saw, what it considered, and why it chose the action it took.

**Target audience:** Developers building agent systems, SREs debugging production incidents, QA engineers investigating test failures.

**What data is required:** Full conversation history (prompts and completions), tool call inputs/outputs, the agent's reasoning or chain-of-thought (where available), context window contents at each decision point.

**Current state:** LangSmith and Arize Phoenix provide good trace-level debugging for LLM calls. Gap: reconstructing the full session-level decision stream (not just individual calls) and understanding context management decisions (what was in the window, what was dropped).

#### A2. Where did the agent get stuck?

**Description:** An agent spent excessive time or tokens on a subtask, entered a retry loop, or repeatedly attempted failing approaches. The practitioner needs to identify bottlenecks and inefficient patterns.

**Target audience:** Developers optimizing agent performance, platform teams managing agent compute costs.

**What data is required:** Timing data per step, token usage per turn, tool call success/failure rates, detection of repeated patterns (same tool called with similar inputs), context compaction events.

**Current state:** OTel spans provide latency data. Token counts are tracked by most tools. Gap: pattern detection (retry loops, repeated failures) requires session-level analysis, not just span inspection.

#### A3. Reproducing agent behavior

**Description:** A practitioner needs to reproduce a specific agent session - either to debug an issue, validate a fix, or create a test case. This requires enough data to replay the session or set up equivalent conditions.

**Target audience:** Developers, QA engineers, researchers studying agent behavior.

**What data is required:** Complete session trajectory including all inputs, model outputs, tool results, and environmental context. Ideally, enough to deterministically replay (though LLM non-determinism makes exact replay difficult).

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

**Current state:** Most agent frameworks have permission systems, but there's no standard for logging permission decisions alongside agent traces. [OCSF](https://schema.ocsf.io/) is relevant prior art for security event modeling, but agent-specific scope and policy decisions are not yet standardized.

#### E3. Audit trail for regulated environments

**Description:** Producing a tamper-evident, complete record of agent actions for regulatory compliance - who initiated the session, what the agent did, what it changed, and who approved each action.

**Target audience:** Compliance teams in regulated industries (finance, healthcare, government), legal teams.

**What data is required:** Immutable session records, user identity, delegation-of-authority records, approval chains, human-in-the-loop checkpoints, policy-check outcomes, complete action logs, timestamps, data lineage, and enough evidence to satisfy audit-log requirements such as [EU AI Act Article 12](https://artificialintelligenceact.eu/article/12/).

**Current state:** No standard addresses this specifically. Teams in regulated industries build bespoke solutions. Relevant prior art includes the [IETF Agent Audit Trail draft](https://datatracker.ietf.org/doc/draft-sharif-agent-audit-trail/) and [OCSF](https://schema.ocsf.io/) for security/compliance event modeling, but the agent-specific audit trail remains an open gap.

---

#### E4. Tamper-evident evidence for audit and dispute resolution

**Description:** A regulated organization must demonstrate, after the fact, what an agent actually did - which tools it called, what side effects occurred in the world, who approved each step, and under what authorization - in a way that is tamper-evident and admissible as evidence. This goes beyond debugging traces: the record must be resistant to modification (by the vendor, the operator, or the agent itself), independently verifiable, and time-bound.

**Target audience:** Compliance officers, security teams, auditors, legal counsel, regulated enterprises (financial services, healthcare, government), and platform vendors selling into those sectors.

**What data is required:** Signed, chain-linked (Merkle-style) event records of agent actions and outcomes, so any single record's alteration is detectable. Write-once-read-many storage semantics for the evidence store. RFC 3161 trusted timestamps (or equivalent) for time-of-event proof. Authorization and approval chain records (who/what approved each consequential action). Declared capability records (manifest, permission scope) linked to observed side effects, so the record can show what was permitted vs what occurred. A comparable evidence-grade ladder so evidence strength can be assessed consistently across vendors.

**Current state:** Vendor traces are mutable and vendor-specific; there is no standard for tamper-evident agent evidence. Adjacent efforts cover pieces (OTel for call telemetry, C2PA for content provenance, RFC 3161 for timestamps, Sigstore for signing) but none addresses agent behavior as an evidence artifact. Gap: an evidence-grade trace interchange format that preserves integrity guarantees end to end. Relevant prior work worth referencing: the [witnessos](https://github.com/narko4u/witnessos) evidence-grade ladder (E0 Declared -> E1 Observed -> E2 Enforced -> E3 Corroborated -> E4 Anchored, where E4 requires external TSA timestamping, Merkle checkpointing, and independent verifiability) offers a concrete reference model for grading evidence strength; [eu-ai-act-compliance-grade](https://github.com/narko4u/eu-ai-act-compliance-grade) maps agent evidence requirements to EU AI Act obligations.

---

### F. Multi-Agent Systems


#### F1. Tracing across agent boundaries

**Description:** When agents delegate work to sub-agents, orchestrate teams of agents, or communicate via shared context, practitioners need end-to-end visibility across the full agent graph.

**Target audience:** Developers building multi-agent systems, platform teams operating them.

**What data is required:** Session-to-session linking (parent/child relationships), shared context tracking, delegation metadata (why this sub-agent was invoked, what it was asked to do).

**Current state:** OTel distributed tracing provides the basic propagation model (trace context). The OTel #2664 proposal addresses agent teams. The [A2A traceability extension](https://github.com/a2aproject/a2a-samples/blob/main/extensions/traceability/v1/spec.md) is relevant prior art for propagating trace context across agent boundaries. Gap: practical conventions for multi-agent tracing that work across frameworks.

#### F2. Understanding agent-to-agent communication

**Description:** When agents communicate (via tool calls, shared memory, message passing), practitioners need to understand what was communicated, whether it was understood correctly, and how it influenced downstream behavior.

**Target audience:** Developers debugging multi-agent interactions, researchers studying emergent agent behavior.

**What data is required:** Inter-agent message content, shared state changes, causal links between agent actions.

**Current state:** Largely unaddressed by existing specs. The OTel #2664 proposal's "team" concept is a starting point, and the [A2A traceability extension](https://github.com/a2aproject/a2a-samples/blob/main/extensions/traceability/v1/spec.md) is relevant prior art for agent-to-agent communication semantics and trace propagation.

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

**What data is required:** Rich session data (full content) that can be analyzed with open-ended methods (LLM-based analysis, clustering, manual review). This requires more than structured metrics - it requires the raw behavioral record.

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

### I. Identity and Ownership

#### I1. Cross-surface identity resolution

**Description:** A single person's (or task's) agent activity is spread across multiple surfaces (IDE, CLI, CI, cloud execution), harnesses, and model providers, each with its own notion of "who" ran the agent - an API key, an OAuth subject, a service account, or an anonymous session. The practitioner needs to resolve all of that activity to a canonical initiating actor (the person, service, or upstream agent that started the work) and to the accountable owner (the organizational unit responsible for its cost and risk), consistently across surfaces and over time.

**Target audience:** Platform teams, security and compliance officers, finance/FinOps teams, engineering managers accountable for agent spend and risk.

**What data is required:** A stable actor identifier per session; the principal reference used on each surface (API key ID, OAuth subject, service-account ID). **Identity:** a mapping from those principals to a canonical initiating actor (person, service, or upstream agent). **Delegation:** the on-behalf-of chain linking them (initiator -> agent -> sub-agent -> tool). **Ownership:** the accountable organizational unit (team, cost center), which may differ from the actor that performed the action.

**Current state:** Assumed but largely unaddressed as an observability concern in its own right. Audit-focused use cases (E3) list "user identity" as required data, and cost use cases (B1, B2) are only meaningful once activity is attributed to an owner, yet no convention specifies how to resolve one actor across surfaces, harnesses, and providers. [OCSF](https://schema.ocsf.io/) models actors and identities for security events and is relevant prior art; OAuth/OIDC subjects and service-account principals are the raw inputs. Gap: a portable way to carry a resolved identity (and its delegation chain) through the trace, so cost, audit, and attribution use cases share one owner definition rather than each re-deriving it.

---

## Contributing

This document is maintained by the Observability Working Group. To add a use case:

1. Choose the appropriate category (A-H) or propose a new one
2. Follow the template: Description, Who cares, What data is required, Current state
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
| I1. Cross-surface identity resolution | | |


---

### Empire Labs Pty Ltd (Security Division) priorities

| Use Case | Priority (Empire Labs) | Notes |
|----------|------------------------|-------|
| A1. Why did the agent do that? | Medium | Useful, well served by existing tools |
| A2. Where did the agent get stuck? | Low | |
| A3. Reproducing agent behavior | Low | |
| B1. Session cost | Low | |
| B2. Cost per outcome | Low | |
| B3. Where is the waste? | Low | |
| C1. Code attribution | Medium | |
| C2. Security review | Medium | |
| D1. Task performance | Low | |
| D2. Regression detection | Low | |
| D3. Model comparison | Low | |
| E1. Agent side effects | **High** | Core of our evidence work |
| E2. Scope enforcement | **High** | Declared vs observed enforcement |
| E3. Audit trail | **High** | Primary product focus |
| E4. Tamper-evident evidence (proposed) | **High** | See proposed use case above |
| F1. Multi-agent tracing | **High** | Delegation chains across agents |
| F2. Agent communication | Medium | |
| G1. Real-time health | Medium | |
| G2. Capacity planning | Low | |
| H1. Failure discovery | Low | |
| H2. Training data | Low | |
| H3. Benchmarking | Medium | |

**Summary for WG:** Empire Labs' priorities cluster in Safety and Compliance (E1-E4) and Multi-Agent Systems (F1), reflecting our focus on evidence-grade observability for regulated and enterprise deployments.
