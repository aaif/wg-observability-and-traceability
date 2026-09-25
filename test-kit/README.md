# Trace-model test kit

This kit holds sample records, expected answers and a runner for the checks in [issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42). Each case is an OTLP/JSON trace export plus the answer a correct reader derives from it. Any OTel tooling can read the records, and no new runtime or backend is needed. Every check here is deterministic; live integration tests belong in a separately labeled job.

## Run it

```sh
pip install -r test-kit/requirements.txt
python3 test-kit/run.py                              # every case answers as expected
python3 test-kit/run.py --reader naive --expect-fail # a reader that trusts the producer fails
python3 test-kit/generate.py --check                 # the fixtures match a rebuild from the seed
```

## Cases

The records follow the support workflow in the execution plan. The agent proposes creating a ticket as action P1, and the action executes. An independently instrumented test service records the creation and signs a receipt.

| Case | What a correct reader answers |
| --- | --- |
| effects-receipt-delivered-twice | The same receipt arrives twice, and the reader reports one confirmed ticket. |
| effects-receipt-missing | No receipt arrives, so the effect is unconfirmed, which is different from "not created". |
| evidence-grade-pair-verifies | The receipt's signature verifies against the service's key, so the effect is confirmed. |
| evidence-grade-pair-fails | Identical to the case above in each producer-authored field, but the signature fails, so the effect is unconfirmed. |

The last two cases are the fixture pair from section 3.3 of the MCP boundary deep dive. A consumer does not report a property it has not re-derived from the record and from the external party that property names. Both records carry the agent's own claim that the effect was externally verified. A reader that repeats that claim cannot tell them apart.

## Readers

The reference reader derives each answer from the records and the test service's public key in the trust directory. The naive reader counts receipt spans and repeats the agent's claim. CI requires the naive reader to fail each case listed as discriminating in run.py, because a case it passes separates nothing.

## Fixtures

The generate.py script rebuilds each fixture from a published seed, and the key it derives signs synthetic receipts only. Ed25519 signatures are deterministic, so a rebuild is byte-identical, and CI checks that. Attribute names are illustrative fixture identities, not proposed OTel attribute names.

## Contributing a case

Copy the TEMPLATE directory and follow its mapping.md. Cases for continuity, calls and retries, and approvals follow the shared contract in [issue #41](https://github.com/aaif/wg-observability-and-traceability/issues/41). The cases here need only the effect and its receipt.
