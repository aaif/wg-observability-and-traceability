# Evidence-grade crosswalk

This page maps three vocabularies for one question: how strongly does a record show that an agent's action took effect? The three are the E0-E4 evidence ladder proposed in [issue #37](https://github.com/aaif/wg-observability-and-traceability/issues/37), the Agent Action Capsule ([draft-mih-scitt-agent-action-capsule-05](https://github.com/action-state-group/agent-action-capsule/blob/91dd7f7faace7bf7091347d70056acdc52582890/spec/draft-mih-scitt-agent-action-capsule-05.md)), and the [observed-effect predicate](https://github.com/probityai/agent-evidence-vectors/blob/v0.25.0/spec/predicates/observed-effect.md) with the terms in [agent-evidence-vocabulary](https://github.com/probityai/agent-evidence/blob/agent-evidence-vocabulary-v0.6.0/packages/vocabulary/vocabulary.yaml). Where a grade is decided only when records are composed, the Capsule column cites the Agent Disclosure Bundle ([draft-mih-zhang-agent-disclosure-bundle-01](https://datatracker.ietf.org/doc/draft-mih-zhang-agent-disclosure-bundle/01/)), written "Bundle -01" below.

All three share one rule, and the test kit checks it: the consumer derives the grade from the evidence, and a value the producer declares never raises it. Section 3.3 of the [MCP boundary deep dive](https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md) states it for this WG. The Capsule draft states it as "a verifier rederives each mode from the evidence present and reports any overclaim". The predicate recomputes `tier` and rejects a record that claims `authoritative` without the evidence for it.

## Grade by grade

| E0-E4 grade (issue #37) | Agent Action Capsule | Observed-effect predicate and vocabulary | Test-kit case |
| --- | --- | --- | --- |
| E0 Declared: agent self-report, no independent verification | `effect_attestation: runtime_claimed`, or `host_served_observed`, which section 5.3 grades equal to it | `witness_scope: SELF`; `observation.vantage: self`; `tier` can only be `voluntary` | The agent's `evidence.externally_verified` attribute in every case is this grade: a claim, not a check |
| E1 Observed: the action observed outside the acting agent | No Capsule value sits here on its own; section 5.3 grades `host_served_observed` with `runtime_claimed`, below `gate_executed` | `observation_vantage: substrate`, `observation_directness: intercepted`; `observation.vantage: below-observed`, `origin: first-hand` | `effects-receipt-missing`, `effects-receipt-delivered-twice` |
| E2 Enforced: a boundary component of the deployment recorded the action | `effect_attestation: gate_executed` (section 5.3, "The commit transited the gate") and the Constraint Record `blocking` flag (section 8.1). Neither says the gate was the only path, and Bundle -01 section 8.1 says that coverage cannot be recomputed from a Bundle's records | `containment_posture` records the boundary the action ran inside; the predicate itself carries no verdicts | No case yet |
| E3 Corroborated: a party that is not the deployment, at PEER or EXTERNAL custody, confirmed the effect | `assurance.cross_party_rung: full_bilateral` (section 5.4.1: `counterparty_ref`, `correlator` and `substantive: true`) plus a non-redundant `agree` join at composition (Bundle -01 sections 7.2.4 and 7.2.5), never a Capsule field alone. `effect_mode: confirmed` with a `response_digest` is the producer's own observation (section 13), so it reaches E2 at most | `witness_scope: PEER` or `EXTERNAL`; `dualValues[].agreement` is `agree`, `disagree` or `one-sided`, derived from the observed and reported values | `evidence-grade-pair-verifies`: a service receipt correlates and its signature verifies |
| E4 Anchored: external timestamp, chain link, anyone can verify | `assurance.ledger_mode: anchored`, credited only after an inclusion proof verifies. It is orthogonal to `cross_party_rung` (section 5.4.1), so it meets E4's anchor condition only on top of an E3 reading | `issuance_time_basis: beacon_anchored`; `observation.priorCommitment.externalAnchor` | No case yet |

## Where the three disagree

Reconciliation has three states in issue #37: `agreement`, `contradiction` and `no_independent_evidence`. The predicate's `dualValues[].agreement` has the same three, as `agree`, `disagree` and `one-sided`. A Capsule has no single field for the third state. It states one value per axis, `effect_attestation: runtime_claimed`, `cross_party_rung: unilateral_fallback` and `provenance_mode.time_rung: self_attested`, and the `cross_party` block is optional, so a Capsule with no exchange is silent rather than stating it. Contradiction arrives as a later Outcome record (section 3.4). The Bundle draft names every state at composition: -01 section 7.2.4 derives `agree`, `mismatch`, `one_sided` or `unjoined`, and section 7.2.5 reports a pair that shares an observer, a `custody_domain` or a `key_id` as redundant rather than corroborating.

Unknown values split by layer. The Capsule registries never reject an unrecognised token during digest verification. Issue #37 and the predicate are closed and fail closed when they grade evidence. Both positions hold at their own layer, and the thread on #37 agreed to state the split: digest verification accepts unknown tokens, and grading never upgrades on one.

A grade and a correlation are different results. `evidence-grade-pair-fails` correlates to the action, and its signature still fails. The E0-E4 ladder needs both readings, so a consumer reports them separately.

## Running the grade-floor checks

The `agent-evidence-vectors` package carries conformance vectors for the predicate. You can install it at a pinned version and replay them, so the kit and the vocabulary above are checked against the same release:

```sh
pip install agent-evidence-vectors==0.25.0
agent-evidence-vectors --corpus vectors-observed-effect
```

The command prints `verdict: every member behaves as MANIFEST.json declares` and exits 0 when every member is accepted or refused as its manifest says.
