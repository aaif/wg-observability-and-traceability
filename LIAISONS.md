# Liaison Roster and Cross-WG Intake Tracker

This document is the Observability & Traceability Working Group's coordination map. It implements the external and internal coordination model described in charter section 8, and it exists so contributors can see, without attending every meeting, which groups this WG tracks, who is driving each relationship, and what is currently moving between groups in either direction.

**Status:** Living working group document - last reviewed 2026-08-22

## External liaison roster

| Group | What they do | Why we coordinate | Liaison | Status | Links |
| --- | --- | --- | --- | --- | --- |
| OpenTelemetry GenAI SIG | OTel cross cutting special interest group that defines GenAI semantic conventions and instrumentation for model calls, agent orchestration, and MCP tool calling. | Charter names this the primary external coordination point and the WG's trace model work must stay compatible with OTel GenAI semantic conventions. | needs owner (Chairs by default per charter section 8, until a member liaison is nominated) | needs owner | [SIG description](https://github.com/open-telemetry/community/blob/main/projects/gen-ai.md) |
| OWASP Agent Observability Standard (AOS) | OWASP project defining an agent standard (instrumentable, traceable, inspectable) that extends MCP, A2A, OTel, and software bill of materials formats for audit and compliance use. | Charter marks this as complementary with a security and compliance focus, with coordination expected on audit trails and side effect tracking. | needs owner (Chairs by default per charter section 8) | needs owner | [OWASP project page](https://owasp.org/www-project-agent-observability-standard/) (redirects to [aos.owasp.org](https://aos.owasp.org/)) |
| W3C Trace Context | W3C Recommendation (published 2021-11-23) defining the `traceparent` and `tracestate` HTTP headers for propagating distributed trace context. | Charter calls this a foundational standard; any trace model deliverable this WG produces must be compatible with it. | needs owner (Chairs by default per charter section 8) | needs owner | [W3C Trace Context spec](https://www.w3.org/TR/trace-context/) |
| Agent Trace (Cursor) | Open specification, published by Cursor, for recording AI code attribution (human vs AI authored code) in version controlled codebases. | Charter lists this as a code attribution spec to track and coordinate with. | needs owner (Chairs by default per charter section 8) | needs owner | [Agent Trace specification](https://agent-trace.dev) (the `cursor/agent-trace` GitHub repo referenced in some third party write ups could not be verified live as of 2026-08-22; use the specification site above) |
| Monocle | GenAI auto instrumentation framework, hosted by LF AI & Data, built on OpenTelemetry for tracing GenAI application code. | Charter calls for reviewing Monocle's metamodel conventions for overlap with this WG's taxonomy and trace model. | needs owner (Chairs by default per charter section 8) | needs owner | [Monocle repository](https://github.com/monocle2ai/monocle) |
| AGNTCY | Open source project building interoperable multi agent infrastructure; its Observe SDK is a framework agnostic, OTel compliant observability SDK for multi agent systems. | Charter calls for coordinating on multi-agent tracing conventions. | needs owner (Chairs by default per charter section 8) | needs owner | [AGNTCY Observe SDK repository](https://github.com/agntcy/observe) |

Per charter section 8, Chairs and Co-Chairs speak for the WG with any external group by default. The WG may nominate a member already active in a given external group as a named liaison for that group; until a nomination is made and recorded here, the entry stays `needs owner` and the Chairs remain the point of contact.

## Internal AAIF coordination

| Group | Relationship | Cadence | Liaison | Status |
| --- | --- | --- | --- | --- |
| AAIF Technical Committee | This WG reports to the TC. | Monthly TC reporting, per the [reporting template](reporting/TEMPLATE.md). | Chairs by default per charter section 8 | in progress |
| MCP Project | Closest internal collaborator; charter calls for a standing liaison between this WG and the MCP maintainers. | Not yet set; to be defined once a liaison is named. | needs owner | needs owner |
| Goose Project | Proving ground and early adopter engagement for this WG's observability guidance. | Not yet set. | needs owner | needs owner |
| AAIF Taxonomy & Landscape workstream | Central cross WG taxonomy effort; this WG both draws terms from it and feeds observability concepts back into it. | Workstream holds a weekly sync on Mondays at 08:30 PST (stated in the header of [taxonomy-data.js](https://github.com/aaif/ws-taxonomy-landscape/blob/main/taxonomy/taxonomy-data.js) in the taxonomy repo); this WG reports and reviews at its own biweekly Wednesday meeting. | needs owner | in progress (the active ask is assigned, see inbound asks below) |
| Identity & Trust WG | Sibling AAIF WG with observability overlap (session, agent, and identity signals in traces). | Not yet set. | needs owner | needs owner |
| Accuracy & Reliability WG | Sibling AAIF WG with observability overlap (evaluation and outcome signals). | Not yet set. | needs owner | needs owner |
| Workflows & Process Integration WG | Sibling AAIF WG with observability overlap (workflow and orchestration trace structure). | Not yet set. | needs owner | needs owner |
| Security & Privacy WG | Sibling AAIF WG with observability overlap (audit trails, side effect tracking); has an open scope review item, see inbound asks below. | Not yet set. | needs owner | needs owner |

## Inbound asks

| From | Ask | Link | Owner | Status |
| --- | --- | --- | --- | --- |
| Security & Privacy WG | Review this WG's scope and identify overlaps with the Security & Privacy WG. | [aaif/wg-security-and-privacy#13](https://github.com/aaif/wg-security-and-privacy/issues/13) | needs owner | needs owner |
| Taxonomy & Landscape workstream | Contribute 10 to 20 candidate terms with a one line disambiguator each; a non member contributor has already posted a draft list of 16 candidate terms in the issue for this WG's editors to accept, reject, or rewrite. | [aaif/ws-taxonomy-landscape#15](https://github.com/aaif/ws-taxonomy-landscape/issues/15) | mr-lee and 91pavan (assigned on the issue) | in progress |

## Outbound items

| To | Item | Link | Owner | Status |
| --- | --- | --- | --- | --- |
| Taxonomy & Landscape workstream | Once the taxonomy v0.2 and trace model crosswalk is published, flag the open questions it identifies for the central taxonomy so the workstream sync can pick them up. | [aaif/wg-observability-and-traceability#10](https://github.com/aaif/wg-observability-and-traceability/issues/10) | needs owner | needs owner |
| OpenTelemetry GenAI SIG, W3C Trace Context maintainers | Once the Agent Behavior Trace Model recommendation plan identifies which existing standards to adopt, extend, or gap fill, share the resulting evaluation criteria and candidate list for external comment. | [aaif/wg-observability-and-traceability#12](https://github.com/aaif/wg-observability-and-traceability/issues/12) | needs owner | needs owner |

## Keeping this current

This tracker follows the same operating cadence as [WORKING-METHODS.md](WORKING-METHODS.md), not a separate process.

- Before each WG meeting, scan this tracker along with open issues and PRs for anything stale or needing agenda time.
- After each WG meeting, update owners, statuses, and next steps here so anyone who missed the meeting can still see the current state of cross group work.
- When another WG or external group makes a new ask, add it to the inbound table with a link, and when this WG has a new outbound item, add it to the outbound table with a link, per the cross WG and external coordination guidance in WORKING-METHODS.md.
- Review this document for currency at the same six month cadence WORKING-METHODS.md sets for living documents, or sooner if a liaison is named or a status changes.
