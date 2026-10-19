# nono and the AAIF working groups

This proposal describes nono's contributions to the Agentic AI Foundation working groups, organized by the layer each group owns. It exists so that one set of shipped facts is mapped three times instead of described three times.

**Status:** proposal, opened 2026-09-16 for discussion in the Observability & Traceability WG (Primitives and Protocol Observability focus group). Nothing here is accepted by any WG yet.

## The rule

`fixtures/kernel-enforced-runtime/nono-evidence-model.md` is the only file that defines a nono field. Every other document maps those fields to a working group's vocabulary and cites `fixtures/kernel-enforced-runtime/nono-evidence-model.md` at a commit SHA. If a WG document and the evidence model disagree, the evidence model is wrong or stale and gets fixed first. WG repositories receive mapping documents and matrix rows, never a second copy of the schema.

## Layer map

One agent action crosses three layers, and three working groups each own one question about it.

```
                        ┌────────────────────────────────────────────┐
  Security & Privacy    │ Should this have been allowed, and what     │
  (enforcement layer)   │ bounds the damage if it was wrong?          │
                        │   kernel LSM · capability broker · proxy    │
                        │   → design pattern, taxonomy terms          │
                        └───────────────────┬────────────────────────┘
                                            │ enforcement decision
                        ┌───────────────────▼────────────────────────┐
  Identity & Trust      │ Who authorized it, on whose behalf, through │
  (authority layer)     │ how many hops, and who answered the approval│
                        │   SPIFFE act chain · approval backend ·     │
                        │   AAuth (branch)                            │
                        │   → delegation and approval evidence        │
                        └───────────────────┬────────────────────────┘
                                            │ identity on the record
                        ┌───────────────────▼────────────────────────┐
  Observability &       │ What is the record, how does it join a      │
  Traceability          │ trace, and what evidence grade is it?       │
  (evidence layer)      │   audit-events.ndjson · hash chain ·        │
                        │   W3C trace context (gap) · OTLP (gap)      │
                        │   → reference architecture, matrix rows     │
                        └────────────────────────────────────────────┘

  01-evidence-model.md defines the fields all three cite.
```

The same `network` record appears in all three: S&P cares that `decision` was enforced before the request left the host, I&T cares that `spiffe_context.delegation` names the authorizer and the depth, T&O cares that `chain_hash` binds the record to a log the agent could not write and that (today) no `trace_id` joins it to a span.

## Folder

| Path | Working group | Artifact type | Target location in the WG repo |
|---|---|---|---|
| `fixtures/kernel-enforced-runtime/nono-evidence-model.md` | none (canonical) | field reference | stays here; cited by SHA |
| `02-observability-traceability/AAIF-REF-ARCH-NONO.md` | T&O | reference architecture in the repo template, graded | `tracing_landscape/05-ai-agent-observability/` |
| `02-observability-traceability/cross-boundary-runtime-and-hitl-rows.md` | T&O | filled matrix rows, vendor-neutral | `working-documents/` (issue #29) |
| `02-observability-traceability/fixtures/` | T&O | verifiable seven-record session and generator | alongside the rows document |
| `03-identity-trust/delegation-and-approval-evidence.md` | I&T | mapping to Clusters 2, 3, 5, 6; AAuth branch status | Reference Architecture working doc (Google Doc), then `AGENDA.md` presentation queue |
| `04-security-privacy/pattern-per-invocation-capability-brokering.md` | S&P | design pattern in problem / context / solution / trade-offs format | `workstreams/design-patterns/` catalog |
| `04-security-privacy/taxonomy-terms.md` | S&P | candidate terms for the end-of-September taxonomy pass | taxonomy PR |

## Why the T&O part belongs in Primitives and Protocol Observability

The WG has three focus groups: Primitives and Protocol Observability, Agent State and Context, and Orchestration and Coordination. The Sept 2 meeting placed below-L7 work in the first. The content confirms the placement on its own terms:

1. **It is primitive-level.** Every record is one decision at one OS or process boundary: a file open, a socket connect, a mediated exec, a credential use. There is no reasoning trace, no memory state, no plan. That rules out Agent State and Context.
2. **It is protocol-level where it is not primitive-level.** The `network` events are per-request observations of HTTP and MCP egress at an L7 proxy, with the decision and credential handling attached. Protocol observability is exactly the focus group's second half.
3. **Its open problem is a primitives problem.** The one thing that would connect this record to the WG's trace model is W3C trace-context propagation across process creation, which is the local-CLI deep-dive's own headline concern and lives in this focus group.
4. **It is single-agent.** Multi-agent coordination is not in these records beyond `chain_depth`. That rules out Orchestration and Coordination as the home, while leaving the delegation fields as an input to that group later.

What T&O should not be asked to hold: whether the enforcement is correct (S&P), and what the identity semantics of the delegation chain mean (I&T). Both are in the layer map above and both have their own folder here.

## Sequencing

1. T&O first, because the record is the thing the other two groups will point at. Issue #29 comment and draft PR, Sept 16.
2. S&P second, because the design-patterns catalog is actively taking entries (kill switches merged Sept 1, memory patterns next) and the taxonomy pass closes end of September. Pattern PR, week of Sept 21.
3. I&T third, through the presentation queue, once the T&O rows have had a review round so the identity mapping cites accepted column names rather than proposed ones.

## Cross-references

- SAF-MCP (OpenSSF): SAF-M-74 Per-Invocation Capability Brokering, where nono is the primary reference implementation. The S&P pattern is the AAIF-facing statement of that mitigation.
- OpenSSF AI/ML Security WG: model and skill signing (OMS). Not mapped here yet; the verification-at-invocation story belongs with the agent-sign submission, not with these three groups.
- OWASP Agent Observability Standard: adjacent evidence container; the T&O prior-work row places nono next to it.
