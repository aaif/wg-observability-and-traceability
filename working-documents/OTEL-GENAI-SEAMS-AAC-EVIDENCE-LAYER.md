# Proposal: Seams Between OTel GenAI Telemetry and Signed Action and Evidence Records

**AAIF Observability & Traceability Working Group - Proposal for discussion**
**Initial draft:** 2026-10-28
**Status:** Proposal, not adopted. For WG discussion as input to the gap register.
**Author:** Steven Mih (participating as an individual)

---

## Purpose

This proposal lists five places where OpenTelemetry GenAI telemetry would have to connect to a signed record of an agent's action and its evidence, so that a span and a record describing the same action can be joined and read the same way.

It is offered as input to the gap register in the [proposed execution plan (PR #60)](https://github.com/aaif/wg-observability-and-traceability/pull/60), which dates a first cut of that register to 2026-10-28. In line with that plan, OpenTelemetry stays the default. Each seam names the existing OpenTelemetry discussion it would join, and nothing here asks the WG to write a competing specification.

**Disclosure:** the author is an author of two of the record formats used as worked references below: the Agent Action Capsule (AAC) and the Agent Evidence Layer (EL) Internet-Drafts. They are used to make each seam concrete, not offered as the only way to fill it. Any signed record format that carries the same fields would meet the same seams.

## Where OTel GenAI stands (checked 2026-10-28)

- The GenAI conventions moved to their own repository, [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) ([semantic-conventions #3696](https://github.com/open-telemetry/semantic-conventions/pull/3696), merged 2026-05-05). That repository has no release yet, and every `gen_ai.*` and `mcp.*` item is `development`.
- Agent spans that exist: `create_agent`, `invoke_agent`, `execute_tool` (handoff is a `transfer` refinement), `invoke_workflow`, `plan`, memory and retrieval. The agent-to-agent model ([#447](https://github.com/open-telemetry/semantic-conventions-genai/pull/447)) merged on 2026-10-26.
- Content capture is opt-in: messages, tool call arguments and tool call results.
- Nothing is merged yet on approvals, authorization, effects, integrity, evidence origin, or references to external records. The one exception is content references: [#490](https://github.com/open-telemetry/semantic-conventions-genai/pull/490), merged 2026-10-27, adds absolute-URI `_ref` attributes for content only.

So telemetry today answers "what ran, and in what order". It does not answer "what was decided, by whom, what changed outside the agent, and who can vouch for it". Signed records can carry those answers. The seams below are where the two need to meet.

## The seams

Seams 2 and 3 are rows already on the WG's "Likely proposals to OpenTelemetry" list in PR #60. Seam 1 is the join that [WG #44](https://github.com/aaif/wg-observability-and-traceability/issues/44) (connect calls, approvals, and external effects) depends on. Seams 4 and 5 already have open OpenTelemetry discussions.

### 1. Span to record join

- **Why:** today a record and the span that observed the same action can only be joined by timestamp. That breaks under retries and concurrency.
- **Missing in OTel:** an attribute that points from a span to an external decision or evidence record. Open discussions: [#239](https://github.com/open-telemetry/semantic-conventions-genai/issues/239) (opaque governance references) and [#589](https://github.com/open-telemetry/semantic-conventions-genai/issues/589) (lineage reference). #490 set a precedent with its absolute-URI `_ref` pattern, but only for content.
- **What a record side adds:**
  - Record to span: the record carries digests of `trace_id`, `span_id` and `parent_span_id`. draft-palanisamy-scitt-aac-otel-00 defines this for AAC. No OpenTelemetry change is needed for this direction.
  - Span to record: the target is a content-addressed, signed record identifier. EL typed links state how records relate to each other.
- **Proposal:** support #239 as a generic, digest-addressed record reference on `execute_tool` and `invoke_agent`, following the #490 `_ref` pattern.
- **Existing implementation:** [capsule-emit](https://github.com/action-state-group/capsule-emit/blob/main/docs/extensions/otel-correlation.md) ships a Python span exporter that writes the digest-only correlation block. It uses a provisional attribute name until OpenTelemetry names one.

### 2. Decision and approval (PR #60 shortlist: approvals)

- **Why:** denied actions often look like they ran, and "approved" does not say whether a human acted or a policy did.
- **Missing in OTel:** nothing merged. Open: [#95](https://github.com/open-telemetry/semantic-conventions-genai/issues/95) (MCP tool approval), [#535](https://github.com/open-telemetry/semantic-conventions-genai/pull/535) (pre-execution tool call decisions), [#445](https://github.com/open-telemetry/semantic-conventions-genai/pull/445) (pause resolved as approved, refused or expired), [#180](https://github.com/open-telemetry/semantic-conventions-genai/issues/180) and [#291](https://github.com/open-telemetry/semantic-conventions-genai/pull/291) (authorization).
- **What a record side adds** (AAC -05, Disposition):
  - `decision`: `accept`, `reject`, `needs_input` or `deferred`.
  - `approver`: a closed enum, `human`, `policy` or `counterparty`.
  - `human_disposed`: true only when a human actually acted. A policy auto-approval is false.
  - `verdict_class`: the terminal reason.
  - A record on every verdict, so a refusal is recorded rather than silent.
- **Proposal:**
  - In #535, record *who decided* separately from *what was decided*, and add a flag for whether a human acted.
  - A refused decision emits no `execute_tool` span.
  - The decision span references its record through seam 1.

### 3. Effect target and status (PR #60 shortlist: the thing an action changed)

- **Why:** the thing an action changed is only recorded inside the full tool arguments, which are opt-in content. And "the tool ran" is not the same as "the effect happened".
- **Missing in OTel:** no effect target, no effect status, and no read versus write distinction. The nearest open discussion is [#373](https://github.com/open-telemetry/semantic-conventions-genai/issues/373) (tool risk attributes).
- **What a record side adds** (AAC -05, Effect Record):
  - `status`: `planned`, `dispatched`, `confirmed`, `failed` or `reverted`.
  - The rule that `confirmed` MUST carry a `response_digest` of the observed response, so "confirmed" means a result was observed and bound.
  - `external_ref`, a join key for later outcomes.
  - `irreversibility_class`.
- **Proposal:** a new OpenTelemetry issue, as the PR #60 shortlist already anticipates. Add an effect target reference and an effect status to `execute_tool`, and mark whether a tool call reads or writes. capsule-emit's span classifier already makes the read/write split from `db.*`, `messaging.*`, `rpc.*` and HTTP attributes, and could serve as evidence.

### 4. Evidence origin

- **Why:** the WG's boundary work separates an observed approval from proof that it was enforced, and a service-side receipt from an attestation. Telemetry has no field that says which kind of value it is carrying.
- **Missing in OTel:** nothing merged. Open: [#386](https://github.com/open-telemetry/semantic-conventions-genai/issues/386) (self-reported vs externally attested), [#406](https://github.com/open-telemetry/semantic-conventions-genai/issues/406) (execution-environment attestation), [#416](https://github.com/open-telemetry/semantic-conventions-genai/issues/416) (content trust). On the WG side: [WG #36](https://github.com/aaif/wg-observability-and-traceability/issues/36) (control-plane telemetry as an evidence source).
- **What a record side adds:**
  - EL -00 `epistemic_type`, with values such as `observed_event`, `system_of_record_fact`, `producer_claim` and `human_report`. It is assigned once, at commit, and is never upgraded.
  - AAC -05 `effect_attestation`, which ranks `gate_executed` above `runtime_claimed` and `host_served_observed`.
- **Proposal:**
  - In #386, add a source-class attribute whose values map onto these types.
  - Adopt the rule that signing a value raises its custody, not its evidence type.

### 5. Integrity without disclosure

- **Why:** arguments and results cannot be proven later if they are captured only as opt-in clear text.
- **Missing in OTel:** [#466](https://github.com/open-telemetry/semantic-conventions-genai/pull/466) (privacy-preserving hashes of tool arguments and results) is open. [#457](https://github.com/open-telemetry/semantic-conventions-genai/pull/457) (action gate and ledgers) and [#438](https://github.com/open-telemetry/semantic-conventions-genai/issues/438) (canonical span hashing) are closed.
- **What a record side adds** (AAC -05, Data-Admission Tiers):
  - Clear-safe: opaque correlation handles.
  - Digest-only: content that must be provable later without being disclosed.
  - Never-enters: end-user and session identifiers and secrets. Hashing a low-entropy identifier does not hide it, because it can be guessed and re-identified. This matches the GDPR point raised on [WG #37](https://github.com/aaif/wg-observability-and-traceability/issues/37).
- **Proposal:** support #466, and add a never-enters rule so that `gen_ai.conversation.id`-class identifiers are left out rather than hashed.

## Kept on the record side

These need no OpenTelemetry change beyond seam 1. They are listed so the WG can decide whether they belong in the trace-model contract.

- **Counterparty confirmation**, as in the WG #44 receipt case. A record carries the other party's confirmation. Telemetry only needs to reference it.
- **Absence.** "Missing means unknown" stays in the WG trace-model contract. A record format can separate a proof that something is absent, a value that was withheld, and an absence that is only asserted.
- **Agent identity and delegation.** Watch [#350](https://github.com/open-telemetry/semantic-conventions-genai/pull/350) and [#345](https://github.com/open-telemetry/semantic-conventions-genai/issues/345). An on-behalf-of principal has no `gen_ai` attribute today.

## Questions for the WG

1. Should seams 2 and 3 be entered in the gap register as evidence on the existing shortlist rows, with captured fixtures from the PR #57 test kit?
2. Should seam 1 (a span to record reference) be added to the shortlist as its own row, or tracked under WG #44?
3. Should seams 4 and 5 go to OpenTelemetry as WG comments on #386 and #466, or wait for the register?
4. Is the "never-enters, not hashed" rule for session and user identifiers something the WG wants in its own trace-model contract?

## References

- AAC: [draft-mih-scitt-agent-action-capsule-05](https://datatracker.ietf.org/doc/draft-mih-scitt-agent-action-capsule/05/). Sections: Effect Record, Disposition, Data-Admission Tiers.
- EL: [draft-mih-agent-evidence-layer-00](https://datatracker.ietf.org/doc/draft-mih-agent-evidence-layer/00/). Sections: Epistemic Type, Typed Links.
- AAC and OTel correlation: [draft-palanisamy-scitt-aac-otel-00](https://datatracker.ietf.org/doc/draft-palanisamy-scitt-aac-otel/00/).
- WG proposed execution plan: [PR #60](https://github.com/aaif/wg-observability-and-traceability/pull/60). WG issues [#36](https://github.com/aaif/wg-observability-and-traceability/issues/36), [#37](https://github.com/aaif/wg-observability-and-traceability/issues/37), [#44](https://github.com/aaif/wg-observability-and-traceability/issues/44), [#47](https://github.com/aaif/wg-observability-and-traceability/issues/47).
- OpenTelemetry GenAI conventions: [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai).
