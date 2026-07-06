# Agent Behavior Trace Model Recommendation Plan

## Purpose

This plan defines how the Observability and Traceability Working Group can produce an Agent Behavior Trace Model recommendation without pre-committing to a new specification.

The recommendation should answer one question:

> Should the working group adopt an existing model, contribute extensions to an existing effort, or create a new AAIF artifact only where a validated gap remains?

This document is a planning aid for issue #12. It is not the recommendation itself and does not choose a winning model.

## Candidate Models And Standards To Compare

The comparison should start with candidates already named in the charter, meeting notes, taxonomy work, or related AAIF project boundaries.

| Candidate | Why compare it | Comparison focus |
| --- | --- | --- |
| OpenTelemetry trace model and GenAI semantic conventions | Primary external telemetry alignment point named by the charter. | Span structure, semantic attributes, context propagation, exporter compatibility, extension path. |
| W3C Trace Context | Foundational propagation mechanism named by the charter. | Cross-process and cross-protocol correlation, trace identifiers, baggage boundaries. |
| OWASP Agent Observability Standard | Security and compliance-adjacent observability effort named by the charter. | Audit trail concepts, side-effect tracking, sensitive-data posture, abuse-case coverage. |
| OpenInference / OpenLLMetry-style conventions | Existing LLM and application tracing conventions referenced by the charter as adjacent work. | LLM call coverage, retrieval/tool coverage, interoperability gaps at agent/session level. |
| MCP observability boundaries | MCP is identified by the charter as the closest AAIF internal collaborator. | Tool calls, resources, prompts, transport boundaries, trace-context handoff. |
| A2A and other protocol observability boundaries | The charter includes protocol interactions and trace portability across agent boundaries. | Agent-to-agent messages, delegation, task continuity, protocol metadata preservation. |
| Agent Trace / code attribution work | Named in the charter as a possible attribution bridge. | Attribution metadata, code or artifact provenance, compatibility with trace events. |
| Monocle metamodel | Named in the charter as a relevant LF AI and Data auto-instrumentation effort. | GenAI metamodel concepts, auto-instrumentation assumptions, mapping to trace spans. |
| AGNTCY Observe SDK | Named in the charter for multi-agent tracing conventions. | Multi-agent trace structure, Observe SDK concepts, interoperability with existing telemetry. |
| Framework-native trace schemas | Many agent frameworks already expose trace-like records. | Practical implementation patterns, gaps, migration burden, vendor lock-in risk. |

## Evaluation Criteria

Use these criteria consistently so the working group can compare candidates without turning the plan into a preference vote.

| Criterion | Question |
| --- | --- |
| Charter alignment | Does the candidate support agent-level observability without defining agent runtime behavior? |
| Existing adoption | Is it already used by agent frameworks, observability tools, standards bodies, or AAIF projects? |
| Agent-level coverage | Does it cover sessions, turns, tool calls, delegation, human checkpoints, outcomes, and side effects? |
| LLM-call compatibility | Can it compose with model-call telemetry rather than replacing it? |
| Context propagation | Can trace context survive agent, tool, protocol, transport, and workflow boundaries? |
| Sensitive-data posture | Can it support redaction, data minimization, retention boundaries, and opt-in content capture? |
| Reasoning boundary safety | Can it represent decision points or reasoning summaries without requiring raw chain-of-thought capture? |
| Audit usefulness | Does it produce evidence that can support debugging, incident review, compliance review, and accountability? |
| Protocol compatibility | Can it map to MCP, A2A, and other protocol interactions without losing protocol-specific metadata? |
| Upstream contribution path | Is there a realistic path to improve an existing standard before creating an AAIF-specific artifact? |
| Implementation burden | Can framework and tool maintainers adopt it incrementally? |
| Vendor neutrality | Does it avoid favoring one vendor, backend, or commercial trace product? |

## Required Inputs Before Recommendation

The recommendation should not be written until these inputs are available or explicitly marked as missing.

| Input | Needed evidence |
| --- | --- |
| Prior work survey | Candidate standards, trace models, observability SDKs, and framework-native trace formats. |
| Use case inventory | Practical agent observability scenarios from member organizations and public contributors. |
| Taxonomy terms | Working vocabulary for spans, runs, tool calls, decisions, evidence, outcomes, and audit handoffs. |
| Gap analysis | Clear statement of what existing candidates do not cover and why the gap matters. |
| Focus group input | Notes from orchestration, primitives, protocol, state/context, and reasoning focus areas. |
| Cross-WG input | Security/privacy, identity/trust, governance/risk, accuracy/reliability, and workflows concerns. |
| External standards input | Feedback or mapping from OTel, OWASP AOS, W3C Trace Context, or other relevant bodies where available. |
| Implementation feasibility | At least one realistic example showing how a candidate can represent a non-trivial agent workflow. |

## Decision Path

The working group can use this sequence to avoid jumping directly to a new specification.

1. **Map candidates to use cases.**
   - If one candidate covers the required use cases with minor interpretation, prefer adoption plus guidance.

2. **Identify extension gaps.**
   - If a candidate is mostly sufficient but lacks specific agent-level fields or conventions, prefer upstream contribution.

3. **Check whether gaps are shared.**
   - If gaps appear only in one framework or product, record implementation guidance rather than creating a standard.

4. **Escalate only validated common gaps.**
   - If multiple focus groups and use cases need the same missing model element, document it as a candidate AAIF gap.

5. **Choose the smallest sufficient recommendation.**
   - Adopt existing model.
   - Adopt existing model plus AAIF guidance.
   - Contribute extensions upstream.
   - Produce a new AAIF artifact only for remaining, validated gaps.

## Expected Recommendation Format

The final recommendation should be concise and reviewable.

| Section | Contents |
| --- | --- |
| Executive summary | One-page recommendation and rationale. |
| Candidate comparison | Matrix using the criteria in this plan. |
| Use case coverage | Which use cases are covered, partially covered, or uncovered. |
| Gap analysis | Specific gaps, why they matter, and whether they are AAIF-specific or upstream candidates. |
| Decision | Adopt, extend, or create-new decision with evidence. |
| Upstream plan | If extension is recommended, list target upstream bodies and proposed contribution shape. |
| Review notes | Open questions, dissenting views, and unresolved risks. |
| Implementation example | Minimal trace example or mapping that demonstrates feasibility without private data. |

## Review Process And Target Milestone

1. Publish this plan as the issue #12 planning artifact.
2. Ask chairs and focus group leads to confirm candidate list and evaluation criteria.
3. Gather inputs from the prior work survey, use case inventory, taxonomy work, gap analysis, and focus groups.
4. Draft the recommendation after the inputs are available.
5. Run a minimum one-week working group review for the recommendation.
6. Route the recommendation to the Technical Committee or relevant external standards bodies if the working group reaches rough consensus.

Target milestone: October 2026, matching the charter's planned Agent Behavior Trace Model Recommendation target.

## Review Checklist For Chairs And Focus Leads

Use this checklist before turning the plan into a recommendation draft.

- Confirm that every candidate model has a named source and comparison reason.
- Confirm that each evaluation criterion maps to a charter goal, use case, or cross-WG concern.
- Confirm that missing inputs are marked explicitly rather than filled with assumptions.
- Confirm that upstream-extension options are considered before proposing a new AAIF artifact.
- Confirm that the recommendation can be reviewed without private member data or vendor-specific trace backends.
- Confirm that any reasoning or decision metadata avoids raw chain-of-thought capture requirements.

## Non-Goals

- This plan does not choose a trace model.
- This plan does not create a new specification.
- This plan does not require raw chain-of-thought capture.
- This plan does not prescribe an observability backend.
- This plan does not replace OTel, W3C Trace Context, OWASP AOS, MCP, A2A, or other existing work.
