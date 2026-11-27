# Observability Best Practices for AI Agents and Multi-Agent Systems

Internet-Draft

- **Intended status:** Informational
- **Authors:** Pavan, Manu, Matt, Johanna, Govind, Matthew, Steven, Mark, Sven, Daniel, Zayne, and contributors to the Agentic AI Foundation (AAIF) Observability & Traceability Working Group
- **Date:** October 2026
- **Expiration date:** To be determined upon submission

## Abstract

AI agents increasingly operate across distributed services, tools, models, protocols, and organizational boundaries. Multi-agent systems introduce additional complexity through delegation, asynchronous execution, dynamic discovery, retries, and interactions between independently operated components. Existing observability practices provide a foundation for monitoring these systems, but operators may still lack sufficient context to reconstruct agent execution, understand failures, correlate actions across systems, evaluate outcomes, and establish accountability.

This document describes implementation-oriented best practices for observing AI agents and multi-agent systems. It covers execution tracing, event and trajectory records, cross-system correlation, semantic consistency, operational metrics, provenance, evaluation, privacy, security, and the relationship between observability and human oversight.

The document encourages reuse of existing protocols, telemetry formats, semantic conventions, and operational practices, including OpenTelemetry and CloudEvents where appropriate. It does not define a new telemetry protocol, agent communication protocol, wire format, or conformance standard.

The purpose is to provide a common foundation for implementation experience and community feedback within the Agentic AI Foundation (AAIF) and related networking and observability communities.

## Status of This Memo

This document is an Internet-Draft and is not a standards-track specification. It is intended to solicit technical feedback and document practical recommendations. It does not represent IETF consensus or establish requirements for protocol interoperability.

Internet-Drafts are working documents and may be updated, replaced, or withdrawn. Readers should consult the current version when referencing this work.

## 1. Introduction

Observability has traditionally focused on understanding the behavior and health of distributed applications through telemetry such as metrics, logs, and distributed traces. These practices remain important for AI systems, but agentic execution introduces additional operational questions.

An agent may interpret a request, select a model, invoke a tool, retrieve external context, delegate work to another agent, evaluate intermediate results, and produce an outcome. The sequence may vary between executions, and individual components may operate across different runtimes, infrastructure providers, and administrative domains.

Consequently, an HTTP request succeeding or an agent process remaining available does not necessarily mean that the intended task was completed correctly. A workflow can terminate without an infrastructure error while using an inappropriate tool, exceeding a budget, relying on stale information, violating an execution constraint, or producing an unverifiable result.

Effective agent observability should therefore support two related but distinct questions:

- **Operational health:** What happened during execution, where did it happen, and what were the performance, reliability, and resource implications?
- **Behavioral understanding:** What actions were taken, how did the workflow progress, which dependencies influenced the result, and what evidence supports the reported outcome?

Observability can provide evidence for debugging, evaluation, incident response, auditing, and human review. It does not, by itself, establish that an agent is trustworthy, safe, correct, or authorized to perform an action.

This document recommends extending established observability practices to agent execution while avoiding unnecessary fragmentation of the existing telemetry ecosystem.

### 1.1. Scope

This document focuses on:

- Agent runs and multi-agent workflow execution.
- Distributed traces and cross-system correlation.
- Events describing meaningful execution steps and state transitions.
- Metrics for reliability, latency, resource consumption, and outcomes.
- Provenance and evidence needed to reconstruct execution.
- Privacy-preserving collection, access control, and retention.
- Operational evaluation and integration with human oversight.
- Interoperability considerations across heterogeneous implementations.

### 1.2. Out of Scope

This document does not define:

- A new agent-to-agent communication protocol.
- A new telemetry transport, serialization format, or trace context format.
- A mandatory agent identity or authorization mechanism.
- A universal agent trajectory schema or evaluation methodology.
- A protocol for intervention, cancellation, or control of remote agents.
- A single numerical score for agent quality, safety, or trustworthiness.

Protocol-level gaps and requirements may be addressed by separate standards activities. This document aims to provide practical guidance that can inform such work without pre-empting it.

## 2. Terminology

The following terms are used throughout this document.

- **Agent:** A software component that selects or performs actions toward a goal, potentially using models, tools, external context, or other agents.
- **Agent run:** An identifiable execution of an agent in response to a request, task, trigger, or delegated assignment.
- **Workflow:** A logical sequence or graph of related operations that contributes to a task outcome.
- **Trajectory:** A temporally ordered or causally related representation of significant execution events, decisions, tool interactions, handoffs, and state transitions.
- **Execution event:** A record of a meaningful occurrence during an agent run, such as a tool invocation, delegation, approval, retry, or completion.
- **Observability:** The ability to infer relevant properties of system behavior from collected telemetry and associated evidence.
- **Provenance:** Information describing the origin, relationships, versions, and processing history of an artifact, observation, or execution result.
- **Correlation context:** Identifiers and contextual information used to relate telemetry produced by different components or systems.
- **Intervention:** An authorized action that changes, pauses, cancels, or otherwise influences ongoing execution.
- **Human oversight:** Processes through which a person reviews, approves, constrains, or intervenes in agent behavior.

## 3. Design Principles

### 3.1. Reuse Existing Standards

Implementations should reuse established telemetry APIs, data models, context propagation mechanisms, and semantic conventions wherever they meet the use case.

OpenTelemetry provides instrumentation and collection mechanisms for traces, metrics, logs, and related telemetry. CloudEvents may be appropriate when representing portable, event-oriented records exchanged between systems.

Implementers should evaluate existing conventions before defining additional attributes or event types. Where extensions are necessary, they should be clearly namespaced, documented, and designed for evolution.

### 3.2. Separate Observation from Control

Telemetry describes what an implementation observes or records. Control mechanisms determine what an implementation is permitted or required to do.

A trace indicating that a budget was exceeded does not itself terminate a workflow. A monitoring alert does not establish authority to interrupt a remote agent.

Systems should make the boundary between observation, policy evaluation, authorization, and enforcement explicit. Where control actions are supported, their authorization and execution outcomes should be recorded separately from the observations that triggered them.

### 3.3. Preserve End-to-End Context

Telemetry should allow operators to relate an agent run to its model calls, tool invocations, retrieval operations, delegated tasks, and downstream service requests.

Correlation should not depend on every component sharing the same runtime, vendor, or administrative domain. Where direct context propagation is unavailable or inappropriate, implementations may use explicit correlation references and documented mapping mechanisms.

### 3.4. Capture Evidence Proportionately

Collect enough information to reconstruct relevant execution without automatically retaining every prompt, completion, retrieved document, or tool payload.

Metadata and structured event records should generally be preferred for routine production operations. Sensitive content should be captured only when justified by an explicit operational, legal, or debugging requirement.

### 3.5. Make Limitations Visible

Missing telemetry, sampling, redaction, partial execution records, clock uncertainty, and failed exporters can affect the conclusions an operator draws.

Implementations should make relevant gaps and limitations discoverable rather than presenting incomplete records as a complete account of execution.

## 4. Observability Model

A useful implementation distinguishes several related levels of observation.

### 4.1 Start with Questions and Outcomes

Instrumentation should begin with the operational questions an implementation needs to answer, rather than with the availability of data. Useful questions include why a task failed, why an agent changed course, where execution became blocked, which resources were consumed, which consequential actions occurred, and what evidence supports the reported outcome.

For each question, implementations should identify the minimum required records, the observation points capable of producing them, the acceptable latency, and the applicable access controls. They should also identify what the available evidence cannot establish.

For example, investigating repeated tool calls may require a task reference, distinct invocation and attempt identifiers, retry reasons, timing, and tool outcomes. Full prompts and tool payloads may be unnecessary. Determining whether an external change occurred may instead require an observation from the affected system.

### 4.2. Infrastructure and Service Level

This level covers conventional distributed-system health, including availability, request rates, error rates, latency, saturation, resource utilization, network behavior, and dependency failures.

Existing service and infrastructure instrumentation should remain available when agent-specific instrumentation is introduced.

### 4.3. Agent Execution Level

This level describes the lifecycle of an individual agent run, including:

- Run initiation and termination.
- Execution status and completion reason.
- Model and tool interactions.
- Retries, timeouts, and cancellation.
- Context acquisition and retrieval.
- Resource consumption and budget utilization.
- Relevant policy decisions and approval outcomes.

### 4.4. Workflow and Multi-Agent Level

This level describes the relationships among steps and participating agents, including:

- Parent and child runs.
- Delegation and handoff.
- Dependencies and execution ordering.
- Parallel execution and synchronization.
- Cross-agent failures and partial completion.
- Workflow-level deadlines and budgets.

A workflow need not execute as a simple tree. Implementations should preserve causal relationships and explicit references when execution is asynchronous or involves shared dependencies.

### 4.5. Outcome and Evaluation Level

This level captures evidence about whether the task achieved its intended result.

Examples include task completion status, validation results, policy compliance outcomes, evaluation scores, human review decisions, and verification references.

Operational success and task success should be represented separately. A successful transport operation does not necessarily imply a successful task, and an evaluation result should not be confused with a definitive proof of correctness.

## 5. Execution Tracing and Trajectory Records

### 5.1. Represent the Run as a Related Sequence of Operations

Implementations should provide a means to reconstruct the significant stages of an agent run. Distributed tracing is a natural foundation where execution can be represented as spans and events.

A representative execution may include:

- Request or trigger received.
- Agent run initialized.
- Context or documents retrieved.
- Model inference requested and completed.
- Tool selected and invoked.
- Tool result received and processed.
- Work delegated to another agent.
- Output validated or evaluated.
- Final result returned or execution terminated.

Not every implementation needs a separate span for every event. The representation should preserve meaningful timing, relationships, and error boundaries without creating excessive telemetry volume.

### 5.2. Distinguish Operations from Events

Spans are useful for operations with a meaningful duration, such as model inference, a tool invocation, or a retrieval request. Events are useful for significant occurrences at a point in time, such as an approval decision or a workflow state transition.

Implementations should use existing tracing semantics consistently rather than representing every occurrence as an independent trace or inventing redundant event structures.

### 5.3. Record Execution Outcomes

For each run, implementations should distinguish at least the following outcomes where applicable:

- Completed.
- Failed.
- Timed out.
- Cancelled.
- Partially completed.
- Blocked pending approval or authorization.
- Unknown or indeterminate.

The reason for termination should be represented separately from the overall status when possible. For example, a workflow can be cancelled because of a deadline, a human intervention, a policy decision, or an upstream dependency failure.

### 5.4. Preserve Partial and Failed Execution

A failure should not erase evidence of preceding operations. Systems should retain sufficient metadata to understand which steps completed, which failed, which were retried, and which remained unresolved.

When telemetry is incomplete, the implementation should avoid implying that an observed terminal event accounts for every operation performed by the system.

### 5.5. Record Important Execution Decisions Without Requiring Private Internal Reasoning

Operationally meaningful decisions may be represented through structured outcomes, selected action identifiers, policy results, tool selection metadata, validation results, and references to relevant inputs.

Observability does not require recording private model reasoning or unrestricted internal deliberations. Implementations should prefer concise, purpose-specific decision records and avoid collecting sensitive internal content without a justified need.

### 5.6 State, Context, and Memory Observability

Agent behavior can depend on context and state that change during execution. Where relevant to investigation, implementations should record references to selected context, memory reads and writes, state transitions, and transformations such as filtering or compaction. They may also record that an input was rejected, unavailable, or omitted when that fact materially affects interpretation.

A bounded context manifest can identify relevant sources, versions, selection outcomes, and protected artifact references without retaining their complete contents. Such a manifest describes what the implementation supplied or made available; it does not necessarily establish what a model relied upon. Digests can support artifact comparison but should not be treated as anonymization.

Resumed execution should retain sufficient references to distinguish restored state from newly acquired context. Observable decisions and concise rationale summaries should remain separate from private internal reasoning and from independently observed behavior. Access to context metadata should not automatically grant access to underlying content.

### 5.7 Tool Actions, Authorization and External Effects

Tool instrumentation should distinguish selection, requested action, authorization decision, dispatch, execution result, and observed external effect. These are related but separate occurrences. Selecting a tool does not establish dispatch, dispatch does not establish execution, and a successful response does not necessarily establish the intended external outcome.

Retries should have distinct attempt identifiers linked to the logical action. Where supported, records should preserve an idempotency reference without exposing credentials or sensitive payloads. Timeouts and cancellation require particular care: an absent response or accepted cancellation request may leave the external effect unknown.

## 6. Cross-System Correlation and Context Propagation

### 6.1. Correlation Identifiers

Implementations should provide identifiers sufficient to relate telemetry to a logical run and its constituent operations.

Where appropriate, these may include:

- A workflow or task identifier.
- An agent-run identifier.
- A distributed trace identifier.
- A parent-run or delegation reference.
- A local operation or event identifier.
- A reference to a relevant artifact or execution result.

These identifiers serve different purposes and should not be treated as interchangeable.

### 6.2. Use Existing Context Propagation Mechanisms

Where distributed tracing is used, implementations should prefer established trace context propagation mechanisms, including W3C Trace Context where supported by the relevant protocols and libraries.

Context propagation should respect trust boundaries. Received trace context is correlation metadata, not proof of identity, authorization, integrity, or provenance.

Implementations should validate incoming context, avoid accepting untrusted baggage indiscriminately, and prevent sensitive data from leaking across administrative boundaries.

### 6.3. Delegation and Asynchronous Execution

When an agent delegates a task, the originating workflow should retain a reference to the delegated operation and its outcome.

If the delegated operation can be represented as a child span in the same trace, that relationship may be appropriate. Where execution crosses incompatible trace contexts, long-lived workflows, or independent systems, implementations may instead preserve explicit links or correlation references.

A delegated task should have enough context to establish its relationship to the initiating workflow without requiring unrestricted propagation of the initiating agent's full prompt, credentials, or private state.

### 6.4 Observation Points and Evidence Quality

Different observation points establish different facts. An agent or framework may report a selected action; a gateway may observe dispatch; a tool may report execution; and a domain system may observe the resulting change. Operating-system and network instrumentation can provide additional evidence about process activity and communication, but may not establish the application-level meaning of those activities.

Records should identify their producer and observation point where relevant to interpretation. Implementations should distinguish agent-reported claims, directly observed occurrences, derived inferences, and independently corroborated results. An observer should not claim facts beyond its visibility.

### 6.5. Clock and Ordering Considerations

Distributed systems cannot always rely on perfectly synchronized clocks. Implementations should distinguish timestamps from causal ordering and use trace relationships, sequence information, or explicit references where necessary.

An apparent timestamp order should not be treated as conclusive evidence of causal order when clock uncertainty or asynchronous delivery may affect the record.

## 7. Semantic Consistency and Interoperability

### 7.1. Prefer Existing Semantic Conventions

Implementations should use existing OpenTelemetry semantic conventions for applicable operations and resources, including supported conventions for HTTP, messaging, exceptions, and generative AI.

Agent-specific fields should complement these conventions rather than duplicate established attributes with different names or meanings.

Because conventions evolve, implementations should document the versions or revisions they support and avoid assuming that every emerging attribute is stable across SDKs and backends.

### 7.2. Document Extensions

When existing conventions do not represent an operationally important agent concept, an implementation may introduce an extension.

Such extensions should document:

- Attribute or event meaning.
- Data type and permitted values.
- Whether the field is required, recommended, or optional within that implementation.
- Privacy and cardinality implications.
- Compatibility and versioning expectations.
- Relationships to existing standards and conventions.

This document does not establish a mandatory shared agent attribute namespace or define a new semantic convention registry.

### 7.3. Portable Event Records

Where an application needs to exchange discrete execution events between systems, an event envelope such as CloudEvents may be useful.

The event envelope and the event's domain-specific payload should be treated as distinct concerns. An envelope alone does not guarantee a consistent interpretation of agent actions, provenance, or outcomes.

Implementations should document event type, source, subject, time, correlation references, and schema evolution behavior as applicable to the selected event model.

### 7.4. Heterogeneous Runtimes

Observability should not require all participating agents to use the same model provider, framework, programming language, or orchestration engine.

Adapters and collectors can help normalize telemetry, but normalization should preserve source-specific information and disclose transformations that could affect interpretation.

Implementations should distinguish directly observed facts from inferred or synthesized records.

## 8. Operational Metrics

Metrics complement traces and event records by identifying trends, regressions, resource constraints, and operational anomalies.

The following categories are useful starting points.

### 8.1. Reliability

Examples include:

- Run completion and failure rates.
- Timeout and cancellation rates.
- Tool invocation failures.
- Retry frequency.
- Delegation and handoff failures.
- Partial-completion frequency.
- Telemetry delivery failures.

### 8.2. Latency and Performance

Examples include:

- End-to-end run duration.
- Model inference latency.
- Tool execution latency.
- Retrieval latency.
- Handoff latency.
- Queueing and waiting time.
- Time to first meaningful result, where applicable.

Percentiles and distributions are often more informative than averages alone, particularly for asynchronous and multi-step workflows.

### 8.3. Resource Consumption

Where supported and appropriate, implementations should record model input and output token counts, tool execution time, retrieval volume, compute utilization, and estimated monetary cost.

Cost calculations should document their assumptions, pricing source, and estimation limitations. Resource metrics should be attributed at useful scopes, such as a run, workflow, or tenant, without creating unbounded metric cardinality.

### 8.4. Workflow Effectiveness

Operational teams may also track:

- Task completion against defined acceptance criteria.
- Validation or evaluation outcomes.
- Human approval and rejection rates.
- Repeated or unproductive tool calls.
- Budget or step-limit exhaustion.
- Frequency of results requiring correction.

These measures are workload-dependent. They should be interpreted alongside task definitions, evaluation methodology, and the consequences of false positives and false negatives.

### 8.5. Avoid Misleading Aggregate Scores

A single score is unlikely to capture reliability, task correctness, cost, security, and autonomy in a meaningful way across all workloads.

Implementations should document the individual measurements and their limitations rather than collapsing unrelated properties into a universal agent quality or trust score.

### 8.6. Detect Behavior Change Across Runs

Observing a single run shows what happened in that run. Operators also need to determine whether an agent behaves differently than it did before, for example after a change to a model, prompt, tool, or skill. Behavior can change while service health remains normal. Latency and error rates may stay constant while the agent retrieves more, produces less, or reaches different decisions.

Implementations that compare behavior across runs should compare a reference period with a recent period for the same agent, and should record the number of runs in each. The comparison can be made from execution metadata that an agent run already produces, without retaining prompts or completions. Useful inputs include:

- Run time and agent identifier.
- Model identifier and version.
- Tool names and tool durations.
- Finish reasons.
- Input and output token counts.
- End-to-end latency.
- The outcome of a decision, where the agent produces one, such as an approval, a denial, or a score.

A report of a change should state which measurements changed and by how much, and which measurements remained stable. It should also state which information was unavailable, such as configuration or tool versions, because missing data is unknown rather than unchanged (see Section 3.5). Versions of the agent, configuration, tools, and instrumentation should be recorded (see Section 9.1), so that a change in how telemetry is produced is not mistaken for a change in agent behavior.

Detecting that behavior changed does not explain why it changed. Implementations should present such a result as a starting point for investigation and avoid reducing it to a single score (see Section 8.5). These practices support the comparison of behavior across versions and configurations described in Section 11.1.

## 9. Provenance, Auditability, and Evidence

### 9.1. Record Relevant Versions and Dependencies

When operationally relevant, execution records should identify versions or references for the agent implementation, configuration, tool definitions, model, workflow, and evaluation criteria.

Implementations may also record references to retrieved artifacts, datasets, or tool results when necessary to explain the outcome.

These records help operators distinguish changes in behavior caused by software updates, configuration changes, model revisions, or altered external inputs.

### 9.2. Distinguish Claims from Evidence

A record stating that an agent completed a task is not equivalent to independent verification that the task was completed correctly.

Where stronger auditability is required, implementations should retain references to validation results, approval records, relevant artifacts, or other evidence supporting the recorded outcome.

The source and verification status of evidence should be clear. An identifier or content hash can help identify an artifact, but does not by itself establish that the artifact is authentic, trustworthy, or authorized.

### 9.3. Integrity and Tamper Evidence

Systems with elevated audit requirements may use append-only storage, access-controlled audit logs, cryptographic integrity mechanisms, or signed records.

Such mechanisms should be selected according to the threat model and operational requirements. Their presence does not eliminate the need for key management, access control, trustworthy collection, and retention policies.

Ordinary telemetry may be sufficient for routine operations. Higher-risk use cases may require selected claims to be supported by independent observations, signed records, trusted timestamps, or external integrity commitments. These mechanisms should be selected according to an explicit threat model rather than applied as a universal maturity requirement.

A signature can support verification of record integrity and attribution to a signing key under stated trust assumptions. A trusted timestamp can support a time claim, and a transparency receipt can support an inclusion claim under the relevant system's assumptions. None of these mechanisms alone establishes completeness, truthful reporting, authorization, correct execution, or real-world effect.

### 9.4. Reproducibility Limitations

Recording versions and inputs can improve reproducibility, but it does not guarantee identical outputs from nondeterministic models, changing external services, or time-dependent data sources.

Implementations should document which aspects of execution can be reproduced and which can only be reconstructed from retained evidence.

## 10. Privacy and Security Considerations

Observability data can contain prompts, personal information, confidential business context, credentials, retrieved documents, tool arguments, and information about internal infrastructure.

Telemetry pipelines should therefore be treated as security-sensitive systems.

### 10.1. Data Minimization

Implementations should collect the minimum information needed for defined operational purposes.

Raw prompts, model completions, tool arguments, and tool results should not be retained by default merely because the instrumentation makes their collection possible.

Where full-content capture is required, it should be subject to explicit configuration, access restrictions, and retention controls.

### 10.2. Redaction and Access Control

Sensitive fields should be redacted, filtered, or excluded before telemetry leaves the relevant trust boundary wherever feasible.

Access to detailed execution records should be restricted according to role and purpose. Access to metadata should not automatically grant access to underlying prompts, documents, or execution artifacts.

### 10.3. Retention and Deletion

Implementations should define retention periods appropriate to operational, contractual, and legal requirements.

Retention policies should account for replicas, exported records, derived datasets, and linked artifacts. Where deletion is required, the implementation should document the extent to which copies and derived records can be removed.

### 10.4. Untrusted Telemetry

Agent-generated events and externally supplied correlation metadata may be incomplete, misleading, malformed, or malicious.

Collectors and analysis systems should validate inputs, limit resource consumption, and avoid interpreting untrusted event content as executable instructions or authoritative security decisions.

### 10.5. Isolation Between Tenants and Administrative Domains

Cross-agent correlation must not become a mechanism for disclosing another tenant's execution history or private context.

Implementations should evaluate information leakage through identifiers, baggage, error messages, event payloads, dashboards, and cross-system references.

### 10.6. Observability Is Not Authorization

A record that an action occurred does not establish that it was authorized. Likewise, successful authentication does not demonstrate that the resulting action complied with policy.

Identity, authorization, policy enforcement, audit, and observability should be integrated where useful but remain conceptually distinct.

## 11. Evaluation and Human Oversight

### 11.1. Observability Supports Evaluation

Execution records can help operators investigate why a task succeeded or failed and compare behavior across versions, configurations, and workloads.

Evaluation should use explicit criteria appropriate to the task. A technically successful run may still produce an incorrect or incomplete result.

### 11.2. Record Oversight Decisions

Where human approval or review is part of the workflow, implementations should record relevant decision metadata, such as the approval state, the action or result under review, the decision time, and the outcome.

Sensitive reviewer content and identity information should be collected only as necessary.

### 11.3. Intervention Requires Separate Control Mechanisms

Systems may use observability signals to trigger alerts, pause execution, request approval, or invoke other control mechanisms.

The authority to perform these actions should be established independently of the telemetry pipeline. Control operations should have defined authorization, failure behavior, and audit records.

Where intervention is unavailable, delayed, or unsuccessful, the system should not imply that observing a problem guarantees that it can prevent or contain the problem.

### 11.4. Human Review Is Not a Universal Guarantee

Human oversight can improve accountability but depends on the quality of evidence, reviewer context, available time, and the consequences of the decision.

Implementations should make uncertainty and missing evidence visible and avoid treating an approval event as conclusive proof of correctness or safety.

## 12. Sampling, Overhead, and Resilience

Detailed agent traces can be expensive, particularly when workflows involve numerous model calls, large payloads, or many delegated operations.

Implementations should balance diagnostic value, telemetry cost, privacy, and system performance.

Recommended practices include:

- Sampling routine successful executions where appropriate.
- Preserving greater diagnostic detail for failures and selected investigations.
- Keeping low-cost aggregate metrics for broader operational visibility.
- Recording when sampling or filtering affects the available evidence.
- Monitoring telemetry pipeline health and dropped records.
- Applying bounded buffering, backpressure, and retry policies.
- Avoiding unbounded cardinality in metric labels.
- Separating critical execution paths from nonessential telemetry export where possible.

Tail-based sampling and failure-triggered collection may improve diagnostic coverage, but implementations should document the possibility that evidence is unavailable because of process crashes, collector outages, or sampling decisions.

Telemetry collection should not itself introduce an uncontrolled failure mode into the agent system.

## 13. Implementation Guidance

An implementation can adopt these practices incrementally.

### 13.1. Baseline

Start by instrumenting the agent run and its major dependencies. Ensure that operators can identify the run, understand its final status, and correlate relevant model, retrieval, and tool operations.

### 13.2. Consistency

Reuse established OpenTelemetry APIs and applicable semantic conventions. Document any additional agent-specific attributes, event types, and relationships.

### 13.3. Failure Analysis

Test whether an operator can reconstruct a failed or partially completed run, including retries, timeouts, delegation failures, and missing telemetry.

### 13.4. Multi-Agent Correlation

Introduce explicit workflow and delegation references. Test correlation across different runtimes and administrative boundaries, including cases where trace context cannot be propagated directly.

### 13.5. Privacy and Governance

Review which telemetry fields contain sensitive data, who can access them, how long they are retained, and how redaction affects investigation and audit requirements.

### 13.6. Operational Readiness

Validate telemetry pipeline behavior under load, collector failure, network partitions, and process termination. Confirm that monitoring remains useful when detailed traces are incomplete.

### 13.7. Evaluation

Define workload-specific outcome criteria and test whether execution records provide enough evidence to investigate incorrect results, not just infrastructure failures.

## 14. Relationship to Existing and Emerging Work

This document is intended to complement existing work rather than establish a competing standards track.

### 14.1. OpenTelemetry

OpenTelemetry provides established APIs, SDKs, semantic conventions, and mechanisms for collecting and exporting telemetry.

Implementations should build on these foundations and coordinate any proposed agent-specific conventions with the relevant OpenTelemetry communities.

### 14.2. CloudEvents

CloudEvents provides a common envelope for describing events across systems. It may be useful for exchanging discrete execution events, provided that the semantics of the event payload are documented separately.

### 14.3. Agentic AI Foundation

The AAIF Observability & Traceability Working Group provides a venue for collecting implementation experience and developing shared best practices for agent execution tracing, cross-system correlation, auditability, and related operational concerns.

This document is intended to preserve that community scope while encouraging interoperability with adjacent ecosystems.

### 14.4. IETF Observability and Network Management Efforts

Relevant IETF work may address network telemetry, management models, distributed systems, security, and the behavior of network management agents.

In particular, the proposed ICON effort, Intervention, Control, Observability of Network Management Agents, as described in ongoing community discussions, may provide a useful point of coordination for use cases, requirements, and protocol-level gaps relating to agent behavior and control.

The exact relationship between this document and such efforts should be established through technical discussion and verified against the relevant working documents as they become available.

This document does not claim to define ICON requirements or substitute for work undertaken through the IETF process. Its intended contribution is practical guidance and implementation experience that can inform adjacent work.

## 15. Open Questions for Community Review

The following questions are offered to guide discussion and future revisions:

- Which existing OpenTelemetry conventions are sufficient for describing agent runs, model operations, tool invocations, and delegated workflows?
- What is the most useful representation of a trajectory when execution spans multiple traces, runtimes, or administrative domains?
- Which identifiers and relationships are essential for reconstructing a multi-agent workflow without leaking sensitive context?
- How should implementations represent incomplete telemetry, uncertain ordering, and inferred execution relationships?

  A practical pattern: when a monitor compares an agent’s behavior before and after a change, it lists what it could not see next to what it saw. For example: output tokens fell, and input tokens rose (seen), config version and tool versions were not received (not seen). That follows 3.5 and 9.1, and it keeps a missing field from being read as “no change.”
- Which operational metrics are useful across workloads, and which should remain application-specific?

  Where prompts and completions are not retained, a small set of metadata fields can still support useful comparison across workloads. These include the run time in UTC, the agent identifier, the model identifier and version, the tool name and duration for each call, the finish reason, input and output token counts, end-to-end latency, and, where the agent produces one, the decision outcome. Section 8.4 refers to human approval rates. The decision an agent itself produces, such as an approval, a denial, or a score, is a separate measurement and can change while latency and token counts remain stable. Where any of these fields are unavailable, the record should say so (see Section 3.5).
- How can provenance and verification evidence be represented without requiring a universal agent identity or trust model?
- What are the most effective practices for privacy-preserving debugging and incident investigation?
- Where should the boundary lie between observational evidence and intervention or control mechanisms?
- Which aspects are best documented as community best practices, and which might eventually justify interoperable semantic conventions or protocol work?
- How can AAIF coordinate with OpenTelemetry and relevant IETF efforts while avoiding overlapping or conflicting specifications?

## 16. Conclusion

Agentic systems introduce operational challenges that extend beyond conventional service health monitoring. Operators need to understand not only whether components are functioning, but also how workflows progress, how agents interact with tools and other agents, what resources execution consumes, and what evidence supports the reported outcome.

These challenges do not require a new observability protocol by default. Existing telemetry standards and distributed-systems practices provide a strong foundation that can be extended through careful instrumentation, consistent semantics, explicit correlation, privacy-aware collection, and transparent treatment of uncertainty.

This document provides a starting point for sharing implementation experience across the AAIF, Linux Foundation observability, OpenTelemetry, and networking communities. Its recommendations should evolve through implementation feedback and coordination with related standards activities.

The immediate objective is to establish useful, interoperable best practices. Any subsequent proposal for additional conventions, protocol requirements, or formal publication should be evaluated separately in light of community feedback, demonstrated gaps, and the appropriate governance process.

## Acknowledgements

The authors welcome contributions from the AAIF Observability & Traceability Working Group, the Linux Foundation observability community, OpenTelemetry contributors, and participants in relevant networking and IETF activities.

## References

### Normative and Informative References

- [W3C-TRACE-CONTEXT] W3C, Trace Context, <https://www.w3.org/TR/trace-context/>
- [OTEL] OpenTelemetry, OpenTelemetry Documentation and Specifications, <https://opentelemetry.io/docs/>
- [OTEL-SEMCONV] OpenTelemetry, Semantic Conventions, <https://opentelemetry.io/docs/specs/semconv/>
- [CLOUDEVENTS] Cloud Native Computing Foundation, CloudEvents Specification, <https://github.com/cloudevents/spec>
- [AAIF-OBS] Agentic AI Foundation, Observability & Traceability Working Group, <https://aaif.io/working-groups/observability-traceability>
- [RFC2119] Bradner, S., Key words for use in RFCs to Indicate Requirement Levels, RFC 2119, March 1997, <https://www.rfc-editor.org/rfc/rfc2119>
- [RFC8174] Leiba, B., Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words, RFC 8174, May 2017, <https://www.rfc-editor.org/rfc/rfc8174>
- [RFC-STYLE] IETF, Guidelines for Writing an RFC, <https://www.rfc-editor.org/>

### References to Be Confirmed

The authors should add the applicable document identifier, revision, and publication status for the ICON effort and any additional IETF work cited in a future revision. References should be verified before submission.
