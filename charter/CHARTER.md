# Agentic AI Foundation Working Group Charter

## Observability & Traceability

### 1\. Working Group Name

| Field | Value |
| :---- | :---- |
| **Working Group Name** | Observability & Traceability |
| **Short Name / Acronym** | OT-WG |
| **Date Approved** | \[YYYY-MM-DD\] |
| **Date Ratified by WG** | 2026-04-15 |
| **Last Updated** | 2026-04-15 |
| **Homepage / Repo** | \[TBD\] |
| **Primary Contact (Chair/Lead)** | Pavan Sudheendra |

---

### 2\. Purpose and Mission

#### Mission Statement

The Observability & Traceability Working Group advances the Agentic AI Foundation's mission by convening practitioners, vendors, and standards bodies to build a shared understanding of agent observability — aligning existing efforts, identifying gaps, and producing guidance or specifications only where no existing body is addressing the need. The WG exists to give practitioners visibility into what AI agents do, how they do it, and what impact they have — enabling debugging, evaluation, safety, and accountability across the agentic AI ecosystem.

#### What this Working Group is not

This WG is not a new standards body. The observability landscape already has active standards efforts (OpenTelemetry GenAI SIG, OWASP AOS, W3C Trace Context, and others). Creating a competing specification body would worsen the fragmentation problem the WG exists to solve. Instead, the WG serves as a **coordination forum**: bringing together the voices from these groups and from AAIF member organizations to build alignment, identify gaps, and direct effort to where it is most needed — including contributing upstream to existing standards bodies where possible.

#### Why this Working Group exists

This Working Group was formed to address:

1. **Fragmented observability landscape.** Over a dozen specifications, conventions, and platforms address pieces of agent observability, but no single effort covers the full picture. Proprietary solutions (LangSmith, Arize, AgentOps, etc.) are proliferating with incompatible trace formats and schemas. Without intervention, vendor lock-in becomes inevitable and cross-framework observability becomes impossible.  
     
2. **Gap between LLM call tracing and agent-level understanding.** Existing standards (OTel GenAI semantic conventions, OpenInference, OpenLLMetry) provide good coverage of individual LLM calls. However, understanding agent behavior at the session or workflow level — across multiple turns, tool invocations, and model interactions — remains an open problem.  
     
3. **Growing demand for agent accountability.** As agents move from prototypes to production, enterprises need ways to audit, evaluate, and explain agent behavior. Multi-modal agentic workflows introduce fundamentally new observability challenges — no standard exists for tracing content lineage, fidelity, or grounding across modality transformations.

#### Guiding Principles

- **Coordinate first, specify only when necessary.** The WG's default action is to align with and contribute to existing standards efforts. New specifications are produced only when a gap analysis demonstrates that no existing body is addressing a clearly identified need — and even then, with the intent of upstreaming the work where possible.  
- **Interoperability over innovation.** Prefer extending and aligning with existing standards over inventing new ones. Where new work is needed, ensure it composes with what exists.  
- **Observable by default.** Agentic systems should be observable out of the box, not as an afterthought.  
- **Move at the speed of the ecosystem.** The agentic AI space evolves rapidly. The WG must deliver incrementally and iterate, not wait for perfection.  
- **Adoption is key.** Deliverables are only valuable if they are adopted. Prioritize practical, implementable standards over theoretically elegant ones.  
- **Vendor and framework neutrality.** No deliverable should advantage a specific vendor, framework, or product.

#### Alignment to Foundation Goals

The work of this WG supports:

- **Interoperability across the agentic AI ecosystem.** By defining common observability conventions, the WG enables agent frameworks, observability platforms, and evaluation tools to discover agents and exchange data without vendor lock-in — extending the same interoperability principle that MCP brings to tool integration.  
- **Trust and safety in agentic AI deployment.** Observable agents are accountable agents. The ability to understand and audit agent behavior is a prerequisite for safe enterprise adoption.  
- **Coordination with adjacent standards bodies.** The WG serves as the AAIF's interface to the OpenTelemetry GenAI SIG, OWASP AOS, and other efforts working on overlapping problems — ensuring alignment rather than fragmentation.

**Context:** The Agentic AI Foundation is hosted within the Linux Foundation and operates with community governance patterns similar in spirit to the Cloud Native Computing Foundation and PyTorch Foundation.

---

### 3\. Scope

#### Technical Mandate

The WG's mandate is **agent-level observability**: the standards, conventions, and guidance needed to understand what agents do, how they coordinate, and what impact they have — across single-agent and multi-agent systems.

This is distinct from, and builds on, LLM-call-level telemetry (the domain of the OTel GenAI SIG). Where existing standards cover individual model calls, this WG addresses the layer above: sessions, workflows, tool use patterns, delegation, side effects, and the behavioral traces that emerge from agent systems operating in the world.

#### Focus Area Model

The WG organizes its technical work into **focus areas** — modular domains of agent observability, each with a defined problem statement, relationship to existing work, and target deliverables. The WG identifies focus areas through its landscape survey and gap analysis, and may form **sub-groups** to pursue them.

Focus areas are not fixed in this charter. The WG may add, merge, or retire focus areas as the landscape evolves and community priorities shift.

##### Founding Focus Area: Agent Behavior Trace Model

The WG's foundational and first-priority focus area is the **Agent Behavior Trace Model**: a core data model for representing the observable behavior of agents and agent systems in a structured, interoperable format. This is the root of the WG's technical work — all other focus groups operate within and extend this model.

The trace model encompasses the key dimensions of agent behavior:

- **Execution structure** — sessions, turns, tool calls, and the hierarchical relationships between them.  
- **Reasoning and planning** — observable records of agent decision-making: plans formed, options considered, strategies selected, and reflections on outcomes. The model provides a structured way to represent these reasoning steps without mandating capture of raw inner-monologue content or proprietary model internals — agents and frameworks control what they choose to expose.  
- **Outcomes and effects** — what the agent produced, what changed in the world, and whether the agent's intent was fulfilled.

The WG will first survey existing trace models and conventions in this space, then determine whether to adopt, extend, or — only if necessary — produce a new specification to address unmet needs.

##### Initial Focus Groups

The following focus groups address specific dimensions of agent behavior observability. Each builds on the Agent Behavior Trace Model and may form a sub-group with dedicated contributors.

**1\. Observability of agentic systems (Orchestration & Coordination)**

This focus group covers how agentic work is structured and handed across agents, services, tools, and people. It focuses on the observable boundaries that make delegated, distributed, or long-running execution understandable and traceable.

- Delegation and hand-offs — tracing when work moves between agents, tools, services, workflows, or human reviewers, what context is passed, and how results flow back.  
- Context propagation and correlation — carrying trace context across agent, model, tool, protocol, and framework boundaries, extending W3C Trace Context and OTel span links.  
- Session and task continuity — maintaining observability when work spans multiple execution boundaries or resumes after interruption.  
- Human-in-the-loop checkpoints — pause, approval, rejection, escalation, and resume semantics for long-running sessions involving human oversight.  
- Responsibility-chain metadata — attribution for which agent or human initiated, delegated, approved, resumed, executed, or modified an action.

**2\. LLM Primitive observability (Execution Surfaces)**

This focus group covers the surfaces through which agent intent becomes an observable action: tools, skills, image ingestion, reasoning tokens and other agent-facing primitives exposed by models or frameworks. The goal is a common vocabulary for what was attempted, what was executed, what happened, and what external effects followed.

- Tool, skill, and primitive execution — structured representation of what the agent invoked, including tool use, skill execution, structured actions, and modality-specific operations that shape agent behavior.  
- Intent, outcome, and side-effect attribution — what the agent requested, what the execution surface returned, and what externally visible state changes resulted.  
- Retry and fallback — observable patterns when execution fails, the agent retries, selects an alternative path, or attempts to undo prior actions.  
- Skill selection, provenance, and composition — which capability was chosen, what alternatives existed, where it came from, and how sub-skills, tools, or other primitives were composed into a larger behavior.  
- Skill-level impact — attributing outcomes, costs, and side effects to the composed capability level, not just to individual primitive calls.

**3\. Protocol Observability**

Protocols such as MCP, A2A, UCP, and others define how agents interact with tools, resources, and each other, and they create the boundaries across which trace data must remain coherent. This focus group covers both protocol-native observability and the conventions needed to make agent trace data portable across systems.

- Protocol normalization — mapping protocol-specific operations into the common trace model while preserving protocol metadata.  
- MCP, A2A, UCP, and other protocol interactions — conventions for tracing tool calls, resource reads, prompt gets, and agent-to-agent or agent-to-system messages.  
- Transport boundaries and context propagation — maintaining trace context across protocol and transport layers.  
- Trace data interchange — common formats and conventions for exporting, publishing, and subscribing to agent trace data, so that downstream consumers (experiment runners, eval harnesses, dashboards, audit systems) can ingest traces without vendor-specific adapters.  
- Alignment with existing telemetry pipelines — ensuring agent trace data can flow through established export paths (OTLP, logging pipelines) and that the WG coordinates with OTel and other bodies on any extensions needed to carry agent-specific semantics.

Coordination with the MCP project and other protocol maintainers is handled through the WG's external liaison process (see Section 8).

**4\. State & Context**

Engineering the context from various sources is key to using agentic systems. We want to understand how to trace and observe the sources and selection of context as well as the state held for agentic systems to work.

- Memory access patterns — observable reads and writes to memory stores (short-term, long-term, episodic, semantic), without requiring exposure of the memory contents themselves.  
- Context assembly — what information sources were consulted, what entered the agent's working context, and what was dropped or compacted.  
- Evidence references — linking agent outputs and decisions to the retrievals, documents, or prior interactions that informed them.  
- Session persistence — maintaining observability across session boundaries when agents resume prior work.  
- Shared knowledge — observability of state accessible to multiple agents, distinct from individual agent memory.

**5\. Agentic Reasoning**

This focus group addresses the observability of agent decision-making: how agents plan, evaluate options, revise their approach, and explain key execution choices. The goal is to represent bounded reasoning artifacts and decision points in a structured way without requiring capture of raw chain-of-thought content or proprietary model internals.

- Planning and decomposition — observable records of how agents break tasks into sub-tasks, form strategies, and sequence actions.
- Evaluation and selection — what options the agent considered, what criteria it applied, and why it chose a particular path.
- Reflection and self-correction — when agents assess their own outputs, detect errors, and revise their approach.
- Reasoning boundaries — structured representation of reasoning summaries, decision points, and rationale at meaningful execution boundaries, without mandating capture of private reasoning traces.

##### Adding Focus Groups

Any WG member may propose a new focus group. Proposals must include:

1. A problem statement grounded in the use case inventory.  
2. A survey of existing work addressing the problem (including whether existing standards are sufficient).  
3. Proposed initial deliverables and timeline.

The WG charters focus groups by consensus. Expected future focus groups include evaluation conventions, multi-modal observability, and identity/trust — but these will be scoped and prioritized based on the gap analysis, not pre-committed.

#### In Scope — Activities

1. **Coordinate with external standards bodies** (OpenTelemetry GenAI SIG, OWASP AOS, W3C, etc.) to ensure alignment, avoid duplication, and contribute upstream where appropriate.  
2. **Survey and catalog** existing agent observability standards, specifications, and implementations, maintaining a living landscape document.  
3. **Define and maintain** a use case inventory capturing the observability needs of AAIF member organizations.  
4. **Develop a shared taxonomy** of agent observability concepts — establishing common vocabulary for the domain.  
5. **Identify gaps** in existing standards and recommend whether the AAIF should adopt, extend, or complement existing efforts.  
6. **Develop specifications or guidance where gaps exist** and no existing standards body is actively addressing the need — prioritized by community need, with upstream contribution as the preferred path.  
7. **Promote interoperability** by defining conformance criteria and, where appropriate, reference implementations or test suites.  
8. **Conduct formal review cycles** (e.g., quarterly) to ensure the landscape document and use case inventory remain current.

#### Out of Scope

1. **Build observability products or platforms.** The WG produces standards, guidance, and reference implementations — not commercial or production-grade tooling.  
2. **Define evaluation methodology.** The WG ensures the data model supports evaluation through metadata hooks, but does not define evaluation methodology, benchmarks, or scoring algorithms.  
3. **Define agent runtime behavior.** How agents make decisions, manage context, or execute tools is the domain of agent frameworks and protocols. The WG standardizes how to *observe and record* that behavior, not how to *perform* it.  
4. **Prescribe specific observability backends.** The WG's deliverables should be backend-agnostic, implementable with any compliant observability stack.  
5. **Duplicate work being done in other standards bodies.** Where the OTel GenAI SIG or OWASP AOS is actively addressing a problem, the WG should coordinate and contribute rather than create competing specifications.  
6. **Governance.** Deferred until liaison with the Governance Working Group is established to determine division of responsibilities.  
7. **Security between agents.** Authentication, authorization, and encryption of agent communication are not in scope. The WG will liaise with the Security & Privacy WG on shared concerns.

#### Assumptions and Dependencies

- **Assumptions:** OpenTelemetry will continue to be the dominant open standard for application telemetry. Agent frameworks will continue to adopt A2A, MCP, and related protocols. Member organizations will contribute use cases and review deliverables.  
- **Dependencies:** OpenTelemetry Semantic Conventions (GenAI SIG) for upstream semantic convention proposals. Other AAIF WGs for coordination on shared concerns (security, governance, identity).

---

### 4\. Goals, Deliverables, and Success Criteria

#### 12-Month Goals

1. **Ratify charter and establish working methods.** Submit charter to governing board, establish sub-group model, and publish working methods document.  
2. **Complete prior work survey and use case inventory.** Establish shared understanding of the landscape and community needs within the WG.  
3. **Complete gap analysis.** Identify the highest-priority gaps not addressed by existing standards, validated by member organization input.  
4. **Produce a recommendation for the Agent Behavior Trace Model** — whether by adopting an existing standard, contributing extensions to an existing effort (e.g., OTel), or producing a new specification where no existing body is addressing the gap. If a new specification is warranted, deliver it with community review and at least one reference implementation.  
5. **Establish active coordination** with the OTel GenAI SIG, OWASP AOS, and at least one other external group — with formal liaison roles assigned.  
6. **Build a healthy contributor community** with regular participation from multiple AAIF member organizations.

#### Planned Deliverables

| Deliverable | Owner | Format | Audience | Target | Status |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Working Methods & Process | Co-Chairs | Guidance document | Internal | July 2026 |  |
| Prior Work Survey (landscape) | Co-Chairs \+ Contributors | Report | Internal | July 2026 | Up for review |
| Use Case Inventory | Co-Chairs \+ Contributors | Living document (first draft) | Internal | July 2026 | Up for review |
| Taxonomy | WG \+ Contributors | Living document (first draft) | Published | June 2026 |  |
| Gap Analysis & Recommendations | WG | Report | Published | October 2026 |  |
| Agent Behavior Trace Model Recommendation | WG | Recommendation (adopt / extend / new spec) | Published | October 2026 |  |
| Agentic Observability Best Practices | WG \+ Contributors | White paper | Published | January 2027 |  |

#### Definition of Done (DoD)

A deliverable is considered complete when:

1. Reviewed and approved via the WG's consensus process (minimum 2-week review period).  
2. Published in the WG's repository with appropriate versioning.  
3. For specifications: at least one reference implementation or conformance test demonstrating feasibility.

#### Success Metrics (KPIs)

- **Coordination:** Active liaison relationships with external standards bodies; upstream contributions (PR, proposal, or joint deliverable) accepted within the first deliverable cycle.  
- **Adoption:** Use cases or deliverable reviews contributed by 10+ AAIF member organizations per deliverable cycle.  
- **Community:** Regular meeting attendance from 5+ organizations; 10+ contributors across deliverables; at least 3 of the 5 focus groups have active leads and regular participation.  
- **Quality:** All published deliverables (taxonomy, gap analysis, recommendation, white paper) reviewed by practitioners from multiple organizations, with feedback incorporated from at least one external standards body. Specifications, if produced, have at least one reference implementation.  
- **Timeliness:** Major milestones delivered within one month of target date.

---

### 5\. Working Methods

#### Operating Model

- **Decision-making:** Consensus-driven, with chair-led resolution when consensus is not immediately clear. Voting as a fallback (see Section 7).  
- **Work tracked in:** GitHub repository under the AAIF organization.  
- **Primary artifacts:** Landscape surveys, use case inventories, gap analyses, recommendations, and guidance documents. Specifications and reference implementations only if warranted by gap analysis.

#### Sub-Groups

For each active focus area, the WG may form a sub-group. Sub-groups:

- Have a designated **lead** responsible for driving deliverables and reporting progress.  
- Operate under the WG's governance and decision-making process (Section 7).  
- Report back to the full WG at regular intervals (at minimum, every other full-WG meeting).  
- May hold their own meetings at a cadence appropriate to their workload.  
- Are chartered and dissolved by WG consensus.

The full WG retains decision authority over all specifications and publications. Sub-groups prepare and recommend; the WG approves.

#### Meetings

| Field | Value |
| :---- | :---- |
| **Cadence** | Biweekly |
| **Duration** | 60 minutes |
| **Time Zone Considerations** | \[TBD\] |
| **Open Meetings** | Yes |
| **Minutes/Notes** | Published in WG repository within 48 hours |
| **Recordings** | Recorded and published (participants are notified) |

#### Communication Channels

- **Async:** Discord and Slack (mirrored). Primary channels for discussion, questions, and coordination.  
- **Sync:** Biweekly Zoom meeting (see Meetings above)  
- **Document drafting:** Google Docs for initial drafting and collaborative editing. Documents move to the WG's GitHub repository as PRs when they are ready for formal review.  
- **Announcements:** Discord \+ Slack

---

### 6\. Membership and Participation

#### Who can participate

Participation is open to all individuals and organizations consistent with AAIF and Linux Foundation policies.

#### Member Roles

- **Participants:** Anyone attending meetings or contributing asynchronously.  
- **Contributors:** Individuals making substantive contributions (issues, PRs, documents, reviews).  
- **Maintainers/Approvers:** Individuals with merge/approval rights in WG repositories, nominated by chairs and confirmed by WG consensus.  
- **Chairs/Co-Chairs:** Responsible for WG operations, facilitation, and external representation.

#### Joining

To join, a participant should:

1. Subscribe to the WG's communication channel(s).  
2. Attend at least one meeting or make an asynchronous contribution.  
3. Sign the DCO/CLA as required by AAIF policy.

#### Expectations

- Follow the AAIF Code of Conduct and collaboration norms.  
- Make contributions in the open (issues, PRs, meeting discussions) whenever possible.  
- Declare conflicts of interest when relevant, particularly when advocating for approaches that benefit a specific product or organization.

---

### 7\. Governance and Decision-Making

#### Leadership Structure

| Role | Name(s) |
| :---- | :---- |
| **Chair** | Pavan Sudheendra |
| **Co-Chair** | Matt Lee |

#### Selection and Term

- **Chairs are selected by:** Election among Contributors, confirmed by the AAIF Technical Committee.  
- **Term Length:** 1 year.  
- **Renewal:** Allowed, maximum 3 consecutive terms.  
- **Removal/Resignation:** A chair may resign at any time. Removal requires a supermajority (2/3) vote of Contributors, or action by the AAIF Technical Committee.

#### Decision Process

- **Default method:** Rough consensus documented in issues and meeting notes.  
- **When consensus cannot be reached:**  
  - **Escalation path:** AAIF Technical Committee.  
  - **Fallback vote rules:** Simple majority of eligible Contributors present at the meeting. One vote per organization to prevent stacking. Vote must be announced on the prior meeting's agenda.

#### Quorum (if voting is used)

Quorum is met by the eligible Contributors present at the meeting where the vote is held. Votes must be announced on the agenda at least one meeting in advance so members can attend.

---

### 8\. Relationship to Other Groups

#### Internal Coordination

- **AAIF Technical Committee:** WG reports to the TC; major deliverables require TC review.  
- **MCP Project:** As a fellow AAIF project, MCP is the WG's closest internal collaborator. The WG will participate in MCP spec discussions where observability is relevant, propose observability extensions (e.g., trace context propagation in MCP transports, observable tool call metadata), and ensure the trace model is compatible with MCP's capability and transport model. A standing liaison between the WG and MCP maintainers will be established.  
- **Goose Project:** As an AAIF-hosted agent framework, Goose is a natural proving ground for the WG's trace model and observability conventions. The WG will engage Goose maintainers as practitioners and potential early adopters, and use Goose's extensible tooling architecture to validate that conventions work in real agent frameworks.  
- **Other AAIF WGs:** The WG will establish liaisons with the Identity & Trust, Accuracy & Reliability, Workflows & Processes and Security & Privacy WGs as they form, to define shared requirements at the observability boundary.

#### External Coordination

| External Group | Relationship |
| :---- | :---- |
| **OpenTelemetry GenAI SIG** | Primary external coordination. WG will contribute to OTel where appropriate rather than duplicating conventions. Formal liaison to be named. |
| **OWASP Agent Observability Standard** | Complementary effort with security/compliance focus. WG will coordinate on shared concerns (audit trails, side-effect tracking). |
| **W3C Trace Context** | Foundational standard for distributed trace propagation. WG deliverables must be compatible. |
| **Agent Trace (Cursor)** | Code attribution spec with potential observability bridge. WG will track and coordinate as appropriate. |
| **Monocle (LF AI & Data)** | GenAI auto-instrumentation framework under LF AI & Data. WG will review metamodel conventions. |
| **AGNTCY** | Multi-agent infrastructure project with Observe SDK. WG will coordinate on multi-agent tracing conventions. |

**Policy for external representation:** Chairs/Co-Chairs may speak on behalf of the WG by default. The WG may also nominate members by vote to represent the WG's interests in external groups they already participate in (e.g., a member active in the OTel GenAI SIG may be nominated as the WG's liaison there). Technical opinions expressed by individual members outside of this role are their own.

---

### 9\. Intellectual Property, Licensing, and Compliance

#### Licensing

- **Code contributions:** Apache-2.0 or MIT (per repository license as approved by AAIF).  
- **Documentation and specifications:** CC-BY-4.0 (or per repository license as approved by AAIF).

#### Contribution Requirements

Contributions must comply with:

- AAIF DCO/CLA policy.  
- Repository contribution guidelines.  
- Review requirements (minimum one approving review from a Maintainer).

#### Antitrust and Competition Law

- Meetings and communications must follow the Linux Foundation's antitrust guidelines.  
- Avoid discussions of pricing, market allocation, competitive strategy, or other restricted topics.  
- Deliverables must be vendor-neutral and not advantage any single member organization's products.

#### Code of Conduct

This WG adheres to the Linux Foundation Project's Code of Conduct.

---

### 10\. Security, Safety, and Responsible AI

#### Security Practices

- **Vulnerability disclosure:** If the WG produces reference implementations, follow AAIF's vulnerability disclosure process.  
- **Sensitive data in WG artifacts:** Avoid including real user data, production prompts, or credentials in issues, documents, or example traces. Use synthetic or redacted data.

#### Domain-Specific Safety Posture

Agent observability data is inherently sensitive — traces can contain prompts, tool call arguments, user data, reasoning artifacts, and a complete behavioral record. When the WG evaluates, recommends, or contributes to any observability standard, it applies the following principles as review criteria:

- **Data minimization.** Standards should capture what is needed for the observability use case, not everything available. Full content logging (prompts, tool outputs) should require explicit opt-in.  
- **Consent and transparency.** Observability data collection should be transparent to users and operators, with clear mechanisms to control what is captured.  
- **Abuse case awareness.** Standards should consider how observability data could be misused (surveillance, discrimination, behavioral manipulation) and address mitigations.  
- **Coordination with Security & Privacy WG.** Privacy and security requirements that go beyond observability-specific concerns are the domain of the Security & Privacy WG. The OT-WG will coordinate with them on shared boundaries.

#### Privacy

- **Personal data in observability data.** Any standard the WG endorses or contributes to should address how personal data in agent traces (prompts, tool outputs, session metadata) is handled — including retention, access controls, and deletion.  
- **Default capture posture.** The WG advocates that observability standards define a minimal default capture level, with richer content capture (full prompts, reasoning traces, tool arguments) available as an explicit opt-in.

---

### 11\. Deliverable Lifecycle and Publication

The WG's primary deliverables are surveys, recommendations, gap analyses, and living documents — not versioned specifications. The lifecycle reflects this.

#### Deliverable Types

- **Living documents** (landscape survey, use case inventory, taxonomy): Updated continuously, date-stamped, no formal versioning. Reviewed quarterly to ensure currency.  
- **Reports and recommendations** (gap analysis, trace model recommendation): Published once, date-versioned. May be superseded by later work.  
- **Specifications** (if produced): Follow SemVer. Subject to the full review and approval process below.

#### Review and Approval

- **Living documents and reports:** Reviewed and approved by WG consensus. Minimum 1-week review period.  
- **Specifications (if produced):** Minimum 2-week WG review period, followed by a 30-day public comment period before ratification.

#### Archival / Deprecation

- A deliverable may be deprecated by WG consensus when it is superseded, rendered unnecessary by upstream standards adoption, or no longer maintained.  
- Living documents with no updates for 6 months should be reviewed for currency or archival.

---

### 12\. Resources and Budget (Optional)

- **Infrastructure:** GitHub repository for deliverables, Google Workspace for collaborative drafting, Zoom for meetings.  
- **Funding requests:** Travel support for WG representation at external standards body events (e.g., OTel community days) and AAIF summits, as available.  
- **Sponsor engagement:** Member organizations are encouraged to contribute engineering time for landscape research, gap analysis, and liaison work with external standards bodies.

---

### 13\. Amendments

This charter may be amended by:

- Consensus of the Working Group, with a minimum 2-week notice period.  
- Amendments are documented in the WG repository.  
- Substantive changes to scope or governance require AAIF Technical Committee approval.

---

### 14\. Ratification

By approving this charter, the Working Group commits to operating transparently, in the open, and in alignment with AAIF and Linux Foundation policies.

| Field | Value |
| :---- | :---- |
| **Approved By** | Observability & Traceability WG (pending TC review) |
| **Date** | \[YYYY-MM-DD\] |
| **Signatories** | \[TBD\] |

---

### Appendix A: Role Descriptions

#### Chair/Co-Chair

Runs meetings, sets agendas, ensures notes are published, drives milestones, represents the WG in cross-WG and external coordination, and ensures the WG operates within its charter.

#### Maintainer/Approver

Responsible for repository health, reviews and merges contributions, ensures release readiness, and provides technical direction on deliverables within their area.

#### Contributor

Provides substantive work items (PRs, documents, issues, reviews), participates in discussions, and helps shape WG deliverables through active engagement.  
