# Working Methods

This document explains how the Observability & Traceability Working Group tracks work, records decisions, and helps contributors find the current state of the group.

The goal is simple: a new or returning contributor should be able to open this repository and answer:

- what is active
- who is driving it
- where the artifact lives
- what the next step is
- how to contribute

## Source of Truth

GitHub is the working group's source of truth for durable work tracking.

- Use issues for work items, coordination threads, decisions, and follow-ups.
- Use pull requests for concrete repository changes.
- Use meeting minutes to summarize discussions and link back to the relevant issues and PRs.
- Use Google Docs for early collaborative drafting when that is the easiest way to write together.
- Move durable artifacts into this repository when they are ready for review, status tracking, or publication.

Slack, Discord, meetings, and email are useful for discussion. They should not be the only place where project status lives.

## Work Tracking

Each meaningful work item should have a GitHub issue unless it is a very small follow-up inside an existing pull request.

An active issue should make the status discoverable without requiring meeting history. It should include:

- **Outcome:** what artifact, decision, or coordination result this issue is expected to produce
- **Owner:** the person or group driving the next step, or `needs owner`
- **Status:** one of `needs owner`, `scoping`, `in progress`, `ready for review`, `blocked`, or `done`
- **Next step:** the next concrete action
- **Links:** related PRs, Google Docs, meeting minutes, standards discussions, or external references

Keep issue updates short and current. If a work item changes direction, update the top comment or add a short status comment rather than relying on scattered discussion.

## Issue Scope

Use issues at two levels:

- **WG-level issues** track shared deliverables, working methods, cross-WG coordination, milestones, and decisions that affect the whole group.
- **Focus-group issues** track work owned by a focus group, such as surveys, gap analyses, problem statements, and proposed guidance.

Focus groups may choose their own cadence and planning style, but their durable status should still be visible through repository issues.

## Pull Requests

Use pull requests for repository artifacts, including meeting minutes, reports, surveys, taxonomy updates, guidance documents, and process changes.

A PR should include:

- the issue it closes or updates
- a short summary of what changed
- any explicit review questions
- any follow-up work that should remain open

Prefer focused PRs. A PR should usually update one artifact or one closely related set of files.

Use the repository PR template when opening a pull request. If a PR does not close an issue, it should still say which issue or meeting action it updates.

## Review Windows

Use these default review windows unless the WG agrees otherwise:

- **Meeting minutes and small documentation fixes:** 2 business days
- **Living documents and reports:** 1 week
- **Specifications or normative guidance:** at least 2 weeks

If a PR needs a longer review window, say so in the PR description.

## Decisions

The default decision model is rough consensus, as described in the charter.

Durable decisions should be recorded in one of these places:

- the issue where the decision was discussed
- the PR where the decision is implemented
- the meeting minutes, with links to the issue or PR

When consensus is unclear, leave the issue open and record:

- the options under consideration
- the known objections or open questions
- the proposed next step
- whether chair or Technical Committee escalation is needed

## Meeting Notes

Meeting notes should be published in the repository when possible.

Meeting notes should link to issues and PRs for any work item mentioned. If a new action item comes out of a meeting, create or update an issue instead of leaving the action item only in the notes.

## Google Docs to GitHub

Google Docs are useful for early drafting and live collaboration. Repository PRs are the durable review and publication path.

When moving a Google Doc into GitHub:

1. Create or identify the tracking issue.
2. Open a focused PR with the document converted to Markdown.
3. Link the original Google Doc when useful for context.
4. Keep the PR description concise and external-facing.
5. After merge, treat the repository version as the durable artifact.

If the Google Doc remains the active drafting surface, the issue should say that clearly and link to it.

## Cross-WG and External Coordination

The WG coordinates regularly with other AAIF groups and external standards efforts. Cross-group work should be tracked in the repository so it is visible to contributors who are not in every meeting or chat thread.

At minimum, coordination tracking should cover:

- the central AAIF Taxonomy/Landscape working group
- OpenTelemetry GenAI
- OWASP Agent Observability Standard
- MCP and other AAIF projects with observability surfaces
- AGNTCY, Monocle, and related Linux Foundation efforts
- Security & Privacy, Identity & Trust, Accuracy & Reliability, and other AAIF WGs where observability is a dependency

Each coordination item should identify an owner or state that an owner is needed.

## GitHub Projects

A GitHub Project board can be useful once the WG has enough active work to justify maintaining one. If used, it should be a view over issues, not a replacement for issues.

Issues remain the source of truth. A board is helpful only if the same status is still understandable from the issue itself.

## Labels

Use the repository's existing labels to make issues easier to filter:

- `documentation` for documents, meeting notes, process, and repo-facing guidance
- `enhancement` for proposed new capabilities, models, recommendations, or standards work
- `help wanted` for work that needs a contributor or owner
- `question` for unresolved design or scope questions

Avoid relying on labels for information that should be in the issue body, such as the next step or owner.

## Contributor Checklist

If you want to contribute:

1. Read the README and charter.
2. Review the open issues.
3. Pick an issue with a clear next step or ask on the issue where help is needed.
4. Comment before doing substantial work so the group can align on scope.
5. Open a focused PR and link it to the issue.
6. Keep follow-up status in the issue or PR so others can discover it later.
