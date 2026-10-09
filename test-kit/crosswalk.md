# Evidence-grade crosswalk

This page maps three vocabularies for one question: how strongly does a record show that an agent's action took effect? The three are the E0-E4 evidence ladder proposed in [issue #37](https://github.com/aaif/wg-observability-and-traceability/issues/37), the Agent Action Capsule ([draft-mih-scitt-agent-action-capsule-05](https://github.com/action-state-group/agent-action-capsule/blob/91dd7f7faace7bf7091347d70056acdc52582890/spec/draft-mih-scitt-agent-action-capsule-05.md)), and the [observed-effect predicate](https://github.com/probityai/agent-evidence-vectors/blob/v0.17.5/spec/predicates/observed-effect.md) with the terms in [agent-evidence-vocabulary](https://github.com/probityai/agent-evidence-vocabulary/blob/main/vocabulary.yaml).

All three share one rule, and the test kit checks it: the consumer derives the grade from the evidence, and a value the producer declares never raises it. Section 3.3 of the [MCP boundary deep dive](https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md) states it for this WG. The Capsule draft states it as "a verifier rederives each mode from the evidence present and reports any overclaim". The predicate recomputes `tier` and rejects a record that claims `authoritative` without the evidence for it.

## Grade by grade

| E0-E4 grade (issue #37) | Agent Action Capsule | Observed-effect predicate and vocabulary | Test-kit case |
| --- | --- | --- | --- |
| E0 Declared: agent self-report only | `effect_attestation: runtime_claimed`, `assurance.attestation_mode: self_attested` | `witness_scope: SELF`; `observation.vantage: self`; `tier` can only be `voluntary` | The agent's `evidence.externally_verified` attribute in every case is this grade: a claim, not a check |
| E1 Observed: a framework or gateway saw the action | `effect_attestation: gate_executed` or `host_served_observed` | `observation_vantage: substrate`, `observation_directness: intercepted`; `observation.vantage: below-observed`, `origin: first-hand` | `effects-receipt-missing`, `effects-receipt-delivered-twice` |
| E2 Enforced: policy enforced at the boundary, denials recorded | A Capsule on every verdict, with `verdict_class: blocked` or `denied` | `containment_posture` records the boundary the action ran inside; the predicate itself carries no verdicts | No case yet |
| E3 Corroborated: independent sources agree | Cross-party assurance; `effect_mode: confirmed` needs a `response_digest` over the observed response | `witness_scope: PEER` or `EXTERNAL`; `dualValues[].agreement` is `agree`, `disagree` or `one-sided`, derived from the observed and reported values | `evidence-grade-pair-verifies`: a service receipt correlates and its signature verifies |
| E4 Anchored: external timestamp, chain link, anyone can verify | `assurance.ledger_mode: anchored`, credited only after an inclusion proof verifies | `issuance_time_basis: beacon_anchored`; `observation.priorCommitment.externalAnchor` | No case yet |

## Where the three disagree

Reconciliation has three states in issue #37: `agreement`, `contradiction` and `no_independent_evidence`. The predicate's `dualValues[].agreement` has the same three, as `agree`, `disagree` and `one-sided`. The Capsule draft has no field for the third state. A `confirmed` effect with no `response_digest` is downgraded to `dispatched_unconfirmed`, which covers the case but does not name it.

Unknown values split by layer. The Capsule registries never reject an unrecognised token during digest verification. Issue #37 and the predicate are closed and fail closed when they grade evidence. Both positions hold at their own layer, and the thread on #37 agreed to state the split: digest verification accepts unknown tokens, and grading never upgrades on one.

A grade and a correlation are different results. `evidence-grade-pair-fails` correlates to the action, and its signature still fails. The E0-E4 ladder needs both readings, so a consumer reports them separately.

## Running the grade-floor checks

The `agent-evidence-vectors` package carries conformance vectors for the predicate. The test-kit workflow installs it at a pinned version and replays them, so the kit and the vocabulary above are checked against the same release:

```sh
pip install agent-evidence-vectors==0.17.5
agent-evidence-vectors --corpus vectors-observed-effect
```

The command prints `verdict: every member behaves as MANIFEST.json declares` and exits 0 when every member is accepted or refused as its manifest says.
