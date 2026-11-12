# Agent identity in telemetry

Status: working draft for [issue #50](https://github.com/aaif/wg-observability-and-traceability/issues/50), 2026-11-12.

A trace should let a relying party correlate an attempt with the decision that governed it. The deciding party keeps the evidence needed to establish who acted, what authority applied, and what outcome the target observed. This draft proposes attribution fields and two synthetic asynchronous examples. The accountability fields and redaction text proposed by Marc Molas Carol are under review in [PR #75](https://github.com/aaif/wg-observability-and-traceability/pull/75).

## Proposed attribution fields

The names below are placeholders for WG review. Identity and action references are high cardinality and belong in approved spans or local records. The stage and result are bounded values suitable for aggregation, subject to the deployment's telemetry policy.

| Field | Meaning | Default placement |
| --- | --- | --- |
| `agent.id` | Opaque agent alias scoped to the relying party | Approved spans in that party's trust domain |
| `agent.issuer` | Issuer reference used in the authority decision | Local audit record |
| `agent.grant_id` | Reference to the grant evaluated by that decision | Local audit record |
| `agent.delegation_depth` | Depth evaluated by the deciding party, when applicable | Local audit record |
| `action.execution_id` | Correlates a specific attempt with its decision and observations | Scoped alias in approved spans, authoritative ID in audit |
| `action.digest` | Digest plus profile identifier for the action document | Local audit record |
| `authority.stage` | `dispatch` or `pre_commit` | Approved spans |
| `authority.result` | `allowed`, `refused`, or `not_evaluated` | Approved spans |

The local record links the decision, attempt and target observation, when available. Accountability is a distinct check described in #75. Its reference and underlying evidence remain with the deciding party. A successful local check establishes accountability at that hop. A claim about continuity across organisations would need its own evidence and sharing rules.

## Propagation and retention

1. The queue carries approved trace context and a scoped execution alias inside the same trust domain. The worker retrieves authorised task inputs through the application channel and evaluates the relevant authority at the applicable boundary. A trace header or alias grants no permissions.
2. The deciding party stores the grant and issuer references, checked status, its age at decision time and the freshness bound, action digest and profile, and observed outcomes in its audit store. Credential material, signatures, raw user data and revocation handles stay outside telemetry. A digest can correlate repeated inputs and stays local by default.
3. Across a trust boundary, send only the context approved for that destination. Keep local accountability references, grant identifiers, status handles and stable identity aliases out of outbound baggage and application metadata. A downstream party that needs accountability performs its own check. If a cross-domain join is authorised, use a scoped reference and retain its mapping in the appropriate audit store.
4. Record a target effect as observed only when there is target-side evidence. A refused check, a stopped job, a timeout, and an unknown target outcome remain separate facts.

## Synthetic asynchronous examples

The examples use fabricated IDs and a local queue. They illustrate the records and their expected relationships. They are not evidence of a vendor run or a target observation.

| Case | Dispatch | Queue / worker | Local audit outcome | Target effect |
| --- | --- | --- | --- | --- |
| Dispatch refused | `refused` | No enqueue | Decision for this attempt recorded at dispatch | `not_observed` |
| Revoked after dispatch | `allowed` | Worker receives the same scoped execution alias. A new pre-commit check sees the revocation and returns `refused`. | Dispatch and pre-commit decisions share one attempt. The latter records the status relied on and its freshness. | `not_observed` |

An illustrative projection for the second case:

```json
{
  "execution_alias": "local-attempt-b",
  "events": [
    {"stage": "dispatch", "authority_result": "allowed"},
    {"stage": "queue_receive"},
    {"stage": "pre_commit", "authority_result": "refused"}
  ],
  "target_effect": "not_observed"
}
```

For a propagation test, assert that the worker sees the same scoped alias after the queue hop, that a dispatch refusal produces no queue event, and that outbound telemetry, headers and application metadata omit the local accountability reference and grant, issuer and status data. A required check that could not complete projects `not_evaluated`. Where no check applied, omit the result. A missing target observation preserves `not_observed`. The two cases above specify expected output for a later instrumented test.

## Review questions

- Which attribution fields should the WG align to the OpenTelemetry GenAI conventions, and which should remain local audit data?
- Can Security & Privacy review the export and baggage boundary together with the accountability proposal in #75?
- What independent target observation is sufficient to record an effect in a future asynchronous run?

Related work: [authority-at-dispatch comparison](https://github.com/aaif/wg-identity-and-trust/issues/13), [evaluation criteria](https://github.com/aaif/wg-observability-and-traceability/issues/66), and [span-to-record joins](https://github.com/aaif/wg-observability-and-traceability/pull/67).
