
# Cross-Boundary Observability Model for Agentic Systems

Status: Working draft for WG discussion and gap-analysis input
Last updated: 2026-08-06

## 1. Purpose and Scope

This document proposes a practical model for analyzing observability gaps at execution boundaries in agentic systems.

It is not a new observability standard. It is a coordination artifact intended to help the WG:

- Compare existing standards and implementations on the same boundary map.
- Identify where interoperability breaks down.
- Prioritize targeted upstream contributions and AAIF recommendations.

## 2. Problem Statement

Agentic systems now span multiple layers:

- LLM primitives such as agents, skills, tools, models, and memory.
- Protocol boundaries such as MCP, A2A, HTTP, and streaming interfaces.
- Infrastructure boundaries such as gateways, runtimes, services, and networks.

Current observability often stops at one layer. As a result, teams can frequently observe one invocation, but cannot reconstruct the full cross-boundary chain of identity, context, delegation, lifecycle, and outcome.

This creates persistent blind spots in:

- Delegation and hand-offs
- Context propagation
- Provenance and trust
- Protocol negotiation and failure modes
- End-to-end responsibility chains

## 3. Boundary Model

The model organizes observability analysis into three layers.

### 3.1 LLM Primitive Layer

Primary entities:

- Agent
- Skill
- Tool
- Model
- Memory

### 3.2 Protocol Boundary Layer

Primary interaction types:

- Discovery
- Negotiation
- Request and response
- Delegation
- Streaming
- Cancellation
- Error handling

### 3.3 Infrastructure Boundary Layer

Primary execution surfaces:

- Gateway
- Runtime
- Service
- Network
- Compute (for example GPU or accelerator resources)

## 4. Cross-Boundary Observability Questions

For each boundary, the same fields should be inspectable:

- Identity: who or what is involved?
- Context: what context was carried across?
- Relationship: what is the parent, child, or causal link?
- Lifecycle: what stage did the interaction reach?
- Outcome: what happened?
- Provenance: where did the resource, skill, or decision come from?
- Security and trust: what policy, consent, or permission applied?
- Timing: how long did each stage take?

## 5. Seed Boundary Matrix

This matrix is intentionally incomplete. It is a seed for the WG gap-analysis process.

| Boundary | Identity | Context | Relationship | Lifecycle | Outcome | Provenance | Security |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Agent -> Skill | Agent instance ID, skill name+version | Task params, conversation slice, invoking prompt/intent | Parent agent -> child skill invocation, call depth | invoked -> running -> returned/errored | Return value, side effects, tokens consumed | Skill source (built-in, org-registered, third-party), skill version hash | Permission scope skill was granted, sandbox/isolation level |
| Skill -> Tool | ? | ? | ? | ? | ? | ? | ? |
| Agent -> Agent | Both agent identities + principal each acts on behalf of | Shared task / session context, delegated sub-goal, budget/quota, memory refs | Delegator/delegate, spawned-by, fan-out siblings | submitted -> working -> input-required -> completed/failed/canceled | Artifact/result handed back, accepted or rejected by delegator | Which model/version made the delegation decision; agent card version | Auth between agents (mTLS/OAuth/SPIFFE), consent scope, downscoped token for further delegation |
| Agent -> MCP Server | ? | ? | ? | ? | ? | ? | ? |
| Agent -> A2A Peer | ? | ? | ? | ? | ? | ? | ? |
| Agent -> Gateway or Runtime | ? | ? | ? | ? | ? | ? | ? |

## 6. How This Supports the AAIF Gap Analysis Work Package

This model is useful to the WG gap-analysis deliverable if used as a comparison framework rather than a standalone proposal.

Recommended usage in the gap-analysis workflow:

1. Select priority boundaries from the matrix (for example Agent -> Agent, Agent -> MCP Server, Agent -> Gateway or Runtime).
2. For each boundary, map which fields are covered by existing efforts (OTel GenAI, OWASP AOS, A2A extensions, MCP practices, OpenInference, vendor tooling).
3. Mark each field as covered, partially covered, or not covered.
4. Capture portability risk (field exists but is not portable across frameworks or vendors).
5. Convert uncovered, high-value fields into proposed upstream contributions.

Why this is additive now:

- It aligns with the charter principle of coordinate first, specify only when necessary.
- It gives a boundary-first lens that complements existing use-case and prior-work documents.
- It makes cross-standard comparison concrete enough to produce actionable recommendations by October 2026.

## 7. Candidate Outputs Enabled by This Model

Ordered roughly from lowest to highest implementation effort.

1. Gap-analysis reference annex
	Boundary-by-boundary table of required fields, existing coverage, and explicit remaining gaps.

2. Conformance checklist and maturity scorecard
	Simple yes or no assessment for boundary propagation and trust-chain metadata.

3. Targeted upstream extensions
	Focused proposals to existing standards bodies (for example A2A extension for delegation-authority and consent-chain metadata, or OTel semantic additions where needed).

4. Reference boundary interceptor pattern
	Lightweight implementation guidance for propagating the agreed fields across MCP clients, A2A clients, and gateway surfaces.

## 8. Immediate Next Steps

1. Pick the first three boundaries for deep analysis in the gap-analysis work package.
2. Assign one owner per boundary and one cross-boundary editor.
3. Define a coverage rubric (covered, partial, missing, non-portable).
4. Produce a first filled matrix pass with citations to prior-work sources.
5. Review in WG and convert priority gaps into upstream action items.

