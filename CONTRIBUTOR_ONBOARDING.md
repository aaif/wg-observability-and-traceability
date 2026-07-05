# Contributor Onboarding

This guide is a practical entry point for people who want to help the Observability and Traceability Working Group.

For policy, scope, and decision-making authority, use the charter as the source of truth. This page only answers: "What should I read, where is work tracked, and how can I make a first useful contribution?"

## Start Here

1. Read the [charter](charter/CHARTER.md) to understand the working group's scope.
2. Skim the latest [meeting minutes](meeting-minutes/) for current context.
3. Review the open [issues](https://github.com/aaif/wg-observability-and-traceability/issues) and [pull requests](https://github.com/aaif/wg-observability-and-traceability/pulls).
4. Pick a small documentation, taxonomy, use-case, or review task.
5. Comment on the issue before taking a larger item so chairs and focus-area leads can avoid duplicate work.

## Access And Communication

The README describes meeting access, working group sign-up, mailing list, and private channel guidance.

Use GitHub for public, asynchronous work:

- issues for work items, questions, and proposed changes
- pull requests for document edits
- meeting minutes for context and decisions
- reporting templates for monthly updates

Some meetings and communication channels may be limited to AAIF members or invited participants. Public GitHub issues and PRs are still the best way to make async work visible and reviewable.

## Current Work Sources

| Source | Purpose |
| --- | --- |
| [README](README.md) | Meeting cadence, chairs, communication, and working group list. |
| [Charter](charter/CHARTER.md) | Mission, scope, focus areas, deliverables, governance, and relationships to other groups. |
| [Meeting minutes](meeting-minutes/) | Recent decisions, action items, and focus-area updates. |
| [Issues](https://github.com/aaif/wg-observability-and-traceability/issues) | Current work queue and requests for help. |
| [Pull requests](https://github.com/aaif/wg-observability-and-traceability/pulls) | Documents currently under review. |
| [Monthly report template](reporting/TEMPLATE.md) | Format for progress, blockers, risks, and next-month focus. |

## Active Focus Areas

The charter describes five initial focus areas. Public meeting minutes include early progress updates for several of them.

| Focus area | What it covers | Where to start |
| --- | --- | --- |
| Agent Behavior Trace Model | Shared model for sessions, turns, tool calls, plans, outcomes, and effects. | Review issue [#12](https://github.com/aaif/wg-observability-and-traceability/issues/12). |
| Orchestration and Coordination | Delegation, hand-offs, human checkpoints, responsibility chains, and cross-boundary context. | Review the charter focus-area section and add use cases or gaps. |
| LLM Primitive Observability | Tool, skill, primitive execution, retry, fallback, side effects, and capability attribution. | Review latest meeting minutes and active landscape/gap-analysis PRs. |
| Protocol Observability | MCP, A2A, UCP, transport boundaries, protocol metadata, and trace data interchange. | Add examples from protocol interactions or review trace-model criteria. |
| State and Context | Memory, context assembly, evidence references, session persistence, and shared knowledge. | Add concrete use cases or prior work references. |
| Agentic Reasoning | Planning, option evaluation, reflection, self-correction, and reasoning boundary summaries. | Review latest meeting minutes and add careful, non-chain-of-thought examples. |

If a focus area has no visible issue yet, open a small issue that states:

- the focus area
- the concrete problem or use case
- any prior work or standard it may overlap with
- what output you are proposing

## First-Time Contributor Checklist

- [ ] I read the charter sections for mission, scope, and out-of-scope work.
- [ ] I checked recent meeting minutes for current context.
- [ ] I searched open issues and PRs for related work.
- [ ] I chose a small first contribution.
- [ ] I avoided adding real user data, credentials, prompts, or proprietary traces.
- [ ] I stated whether the contribution is a new idea, review comment, document edit, or prior-work reference.
- [ ] I linked any relevant standards, projects, or issues.
- [ ] I used neutral language and avoided vendor-specific claims unless the example requires them.

## Good First Contributions

Good first contributions are narrow and reviewable:

- add one missing prior-work reference with a short reason it matters
- add one agent observability use case to the appropriate issue or PR
- review a document PR and leave specific comments
- clarify a confusing term in a draft document
- propose acceptance criteria for an open work item
- summarize overlap between a focus area and an existing standard
- add a meeting-minutes follow-up issue when an action item has no tracker

Avoid starting with:

- a new specification
- a broad rewrite of the charter
- a vendor pitch
- content that duplicates existing standards without explaining the gap
- examples containing sensitive or proprietary trace data

## Picking Up Work From Issues

Before opening a PR:

1. Read the issue body and acceptance criteria.
2. Check linked PRs and comments.
3. Comment with the part you plan to handle.
4. Keep the PR focused on one issue or one document area.
5. In the PR body, link the issue and describe what remains out of scope.

Useful current entry points:

- [#8 Create onboarding checklist and focus-group entry points](https://github.com/aaif/wg-observability-and-traceability/issues/8)
- [#9 Prioritize the use-case inventory after PR #6 lands](https://github.com/aaif/wg-observability-and-traceability/issues/9)
- [#10 Publish taxonomy v0.2 and trace-model crosswalk](https://github.com/aaif/wg-observability-and-traceability/issues/10)
- [#11 Establish liaison roster and cross-WG intake tracker](https://github.com/aaif/wg-observability-and-traceability/issues/11)
- [#12 Plan Agent Behavior Trace Model recommendation](https://github.com/aaif/wg-observability-and-traceability/issues/12)

## Proposing Document Edits

For living documents:

- prefer small PRs
- explain the reason for the change
- cite the issue, meeting note, or charter section that motivated it
- use synthetic examples
- keep unresolved questions in comments or follow-up issues

For new documents:

- start with an issue first
- list the intended audience
- list the expected review path
- avoid presenting draft content as a final WG position

## Contacting Or Self-Nominating For Focus Areas

Use public GitHub first:

1. Open or comment on an issue for the focus area.
2. State your interest and relevant experience.
3. Ask where current work is tracked if it is not visible in the repository.
4. If you are eligible for working group channels or meetings, follow the README sign-up and communication guidance.

Do not assume that a GitHub comment assigns you as a focus-area lead. Leadership, liaison, and representation roles follow the working group's governance and chair process.

## Review Etiquette

- Be specific: quote the sentence, section, or acceptance criterion you are addressing.
- Separate blocker feedback from optional polish.
- Prefer "this may overlap with..." over "this is wrong" when comparing standards.
- Ask for missing context instead of guessing private working group decisions.
- Keep antitrust, privacy, and sensitive-data guidance in mind.

## Sensitive Data Reminder

Do not include:

- production prompts or completions
- user data
- customer names
- credentials or tokens
- proprietary traces
- confidential incident data

Use synthetic examples or redacted snippets when a concrete example is needed.
