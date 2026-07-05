# Liaison Roster And Cross-WG Intake Tracker

This tracker records the external standards groups, AAIF working groups, and related projects the Observability and Traceability Working Group expects to coordinate with.

The goal is visibility, not assignment by assumption. Where no public liaison or owner is named in this repository, the owner is marked `TBD`.

## How To Use This Tracker

- Add a row when the working group identifies a coordination dependency.
- Keep owner fields explicit: name the acting liaison only after the working group or chairs have confirmed it.
- Use `Inbound ask` for requests coming to this working group.
- Use `Outbound follow-up` for questions, proposals, or updates this working group owes another group.
- Link to issues, PRs, meeting minutes, or external artifacts when available.
- Do not record private contact details, member-only channel links, or non-public meeting notes.

## External Groups And Standards Bodies

| Group | Why this WG tracks it | Acting liaison or owner | Cadence | Inbound ask | Outbound follow-up | Public tracking |
| --- | --- | --- | --- | --- | --- | --- |
| OpenTelemetry GenAI SIG | Primary external coordination point for telemetry conventions; the charter says the WG should contribute to OTel where appropriate. | TBD | TBD | TBD | Identify where agent-level trace requirements extend or complement OTel GenAI semantics. | TBD |
| OWASP Agent Observability Standard | Complementary effort with security and compliance focus, especially audit trails and side-effect tracking. | TBD | TBD | TBD | Compare audit, side-effect, and sensitive-data guidance before proposing overlapping work. | TBD |
| W3C Trace Context | Foundational trace propagation standard that WG deliverables should remain compatible with. | TBD | TBD | TBD | Track context propagation requirements across agent, tool, model, protocol, and transport boundaries. | TBD |
| Agent Trace (Cursor) | Charter lists it as a code-attribution spec with a possible observability bridge. | TBD | TBD | TBD | Clarify whether attribution metadata should inform the Agent Behavior Trace Model recommendation. | TBD |
| Monocle (LF AI & Data) | Charter identifies Monocle as a GenAI auto-instrumentation framework whose metamodel conventions should be reviewed. | TBD | TBD | TBD | Compare metamodel concepts with WG taxonomy and trace-model candidate criteria. | TBD |
| AGNTCY | Charter identifies AGNTCY and its Observe SDK as relevant to multi-agent tracing conventions. | TBD | TBD | TBD | Track multi-agent tracing concepts that may overlap with orchestration and protocol observability. | TBD |
| Protocol maintainers beyond MCP | The charter names A2A, UCP, and other protocol interactions as part of protocol observability. | TBD | TBD | TBD | Identify protocol metadata needed for portable trace data without duplicating protocol-specific specs. | TBD |

## AAIF Internal Coordination

| AAIF group or project | Why this WG tracks it | Acting liaison or owner | Cadence | Inbound ask | Outbound follow-up | Public tracking |
| --- | --- | --- | --- | --- | --- | --- |
| AAIF Technical Committee | Major deliverables require TC review; monthly reports and recommendation milestones flow through the TC. | Chairs | Monthly or as requested | Review progress, blockers, and major deliverables. | Publish monthly report updates using the reporting template. | `reporting/TEMPLATE.md` |
| MCP Project | The charter calls MCP the closest internal collaborator for trace context propagation and observable tool-call metadata. | TBD | TBD | TBD | Identify MCP observability requirements for resources, tools, prompts, transports, and capability metadata. | TBD |
| Goose Project | The charter identifies Goose as a proving ground for validating trace model and observability conventions in an AAIF-hosted agent framework. | TBD | TBD | TBD | Identify a practical validation scenario once candidate trace conventions are ready. | TBD |
| Taxonomy and Landscape Workstream | Meeting minutes describe a cross-working-group taxonomy/landscape workstream requiring participation from each group. | TBD | TBD | Taxonomy feedback and shared vocabulary input. | Provide observability terms, trace-model concepts, and landscape references. | TBD |
| Identity and Trust WG | Charter expects coordination on identity-related observability boundaries. | TBD | TBD | TBD | Clarify identity and attribution metadata needed in agent traces without defining authentication policy. | TBD |
| Security and Privacy WG | Charter expects liaison on security, privacy, sensitive data, and shared boundaries. | TBD | TBD | TBD | Align on sensitive trace data, data minimization, audit, and privacy guidance. | TBD |
| Governance, Risk and Regulatory WG | Charter defers governance until liaison with the Governance Working Group clarifies division of responsibilities. | TBD | TBD | TBD | Clarify how observability evidence supports governance without becoming governance policy. | TBD |
| Workflows and Process Integration WG | Charter lists workflows, delegation, human checkpoints, and coordination as observability concerns. | TBD | TBD | TBD | Align on workflow, handoff, and human-in-the-loop trace semantics. | TBD |
| Accuracy and Reliability WG | Trace data may support reliability review, debugging, and evaluation feedback loops. | TBD | TBD | TBD | Clarify which reliability signals belong in agent trace metadata versus evaluation methodology. | TBD |

## Intake Queue

Use this table for concrete cross-group requests.

| Date | Source group | Request or question | Direction | Owner | Status | Link |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-25 | WG meeting minutes | Focus group leaders should sync with chairs on one place to discover all activities. | Internal | Chairs / focus group leads | Open | `meeting-minutes/2026-06-25.md` |
| 2026-06-25 | WG meeting minutes | Community members should review taxonomy terms and add issues for specific items they want covered. | Inbound | TBD | Open | `meeting-minutes/2026-06-25.md` |
| 2026-06-25 | WG meeting minutes | Consider inviting Owen Junji to discuss the agentic resource discovery specification and observability correlations. | Outbound | Chairs | Open | `meeting-minutes/2026-06-25.md` |
| 2026-06-11 | WG meeting minutes | Raise asynchronous coordination through PRs or issues with taxonomy workstream leaders. | Outbound | Matt or nominated lead | Open | `meeting-minutes/2026-06-11.md` |
| 2026-06-11 | WG meeting minutes | Coordinate with other working group meetings and access paths. | Outbound | Pavan | Open | `meeting-minutes/2026-06-11.md` |

## Review Checklist

- [ ] Each row has an owner or is marked `TBD`.
- [ ] Each row has a clear inbound ask or outbound follow-up, even if it is `TBD`.
- [ ] Private contact details are omitted.
- [ ] Links point to public issues, PRs, meeting minutes, charter sections, or public external artifacts.
- [ ] The tracker is updated when a liaison is named, a cadence is set, or a follow-up is closed.
