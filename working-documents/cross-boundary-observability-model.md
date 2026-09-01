
# Cross-Boundary Observability Model for Agentic Systems

Status: Working draft for WG discussion and gap-analysis input
Last updated: 2026-08-25

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

## 5. Boundary Requirements Matrix

This is a living requirements matrix for the WG gap-analysis process. Protocol-specific entries reflect [MCP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/) and [A2A 1.0](https://a2a-protocol.org/v1.0.0/specification/); implementation coverage still needs to be assessed separately.

| Boundary | Identity | Context | Relationship | Lifecycle | Outcome | Provenance | Security | Timing |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Agent -> Skill | Agent instance ID; skill ID, name, and version | Task parameters, selected conversation/context slice, invoking intent, constraints, budget | Parent agent -> child skill invocation; call depth; governing decision | discovered -> selected -> invoked -> running -> returned/errored/canceled | Return value or artifact, side effects, token/resource use, error details | Skill source and publisher, registry entry, version or content digest; producer and evidence class | Granted permission scope, approval decision, sandbox/isolation level, data-access policy | Selection, queue, start, first-output, and end timestamps; queue and execution duration; timeout, retry, and backoff time |
| Skill -> Tool | Skill ID; tool name, version, server/endpoint | Arguments, input/output schema, task and trace context, constraints | Skill is caller-of-record; invocation links to governing skill/agent decision and resulting observation | discovered -> called -> executing -> input-required/completed/error/canceled/timeout | Structured/unstructured output, protocol or execution error, exit/status code, external side effects | Tool definition and registry/server source, publisher/approver, schema/version digest; producer and evidence class | Credential reference and scope (never secret value), authorization decision, confirmation, sandbox and egress policy | Request, execution-start, progress, first-result, and end timestamps; execution duration; timeout, retries, and backoff |
| Agent -> Agent | Both agent identities and versions; principal each represents | Shared task/context IDs, delegated goal, messages/artifact refs, constraints, budget/quota, memory refs | Delegator/delegate; parent/child or referenced task; fan-out/fan-in; governing decision | proposed -> accepted/rejected -> working -> input-required/auth-required -> completed/failed/canceled | Artifact/result and status; partial completion; acceptance/rejection by delegator; error details | Agent description/card and provider, model/runtime version, delegation-decision record; producer and evidence class | Mutual authentication, authorization and consent scope, delegation depth, downscoped credentials, policy decisions | Discovery and negotiation latency; submit/accept/start/status/end timestamps; time to first update/artifact; active, waiting-for-input/auth, and total duration |
| Agent -> MCP Server | ? | ? | ? | ? | ? | ? | ? | ? |
| Agent -> A2A Peer | A2A client and remote agent identities/versions; represented principals; Agent Card provider; tenant | `messageId`, `taskId`, `contextId`, referenced tasks, parts/artifacts, accepted modes, extension and trace metadata | Client/server and delegator/delegate; message -> task -> artifact; related/refinement task links | message-only response or submitted -> working -> input-required/auth-required -> completed/failed/canceled/rejected; terminal tasks are immutable | Response message or task artifacts, status and status message, partial result, protocol error, acceptance/rejection | Agent Card, provider/version, supported interface/protocol version, extension URIs, card signature; producer and evidence class | TLS; declared auth scheme (API key, HTTP auth, OAuth/OIDC, mTLS); caller scopes, task authorization, consent/delegation scope, webhook verification | Send/acknowledge/start and status timestamps; time to first status/artifact; stream/poll/push delay; active, interrupted, and total task duration; cancellation/retry time |
| Agent -> Gateway or Runtime | ? | ? | ? | ? | ? | ? | ? | ? |
| Agent -> Human (HITL) | ? | ? | ? | ? | ? | ? | ? | ? |


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

Given what's actually happening in the ecosystem right now, a few concrete, credible deliverables — roughly in order of effort:
1. A gap-analysis reference document —The first place someone can look up "for boundary X, here's what should be carried, and here's which existing standard almost covers it, and here's the exact gap." 
2. A submission to A2A's extension mechanism — since A2A already has a working extension slot and four precedent extensions (Secure Passport, Timestamp, Traceability, Agent Gateway Protocol), a fifth extension specifically for delegation-authority/consent-chain tracking is a realistic, scoped contribution — not a new protocol, a patch to an existing one.
3. A reference middleware/interceptor library — a small SDK that sits at each boundary (MCP client, A2A client, gateway) and auto-populates the matrix fields into OTel spans. Given the market is already building auto-instrumentation for 40+ AI frameworks, positioning this as "the missing agent-to-agent layer" on top of existing instrumentation is more adoptable than a standalone spec.
4. A conformance checklist / maturity model — turn the matrix into a scorecard ("does your gateway propagate delegation identity? Y/N — does it propagate consent scope? Y/N") that vendors or platform teams can self-assess against. This is the lightest-weight version and the fastest to produce, and it doubles as a procurement/audit tool for enterprises deploying multi-agent systems who need to answer "can we trace what our agents authorized each other to do" for compliance reasons.


## 8. Immediate Next Steps

1. Pick the first three boundaries for deep analysis in the gap-analysis work package.
2. Assign one owner per boundary and one cross-boundary editor.
3. Define a coverage rubric (covered, partial, missing, non-portable).
4. Validate each matrix row against prior-work sources and record coverage, portability, and citation gaps.
5. Review in WG and convert priority gaps into upstream action items.

