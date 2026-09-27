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

## Which document each answer follows

Each case carries `basis.json`, which names the document its expected answer follows, so a reader can decide whether a case is in its scope without opening `expected.json`. The two effects cases follow the example in [issue #42](https://github.com/aaif/wg-observability-and-traceability/issues/42), which section 1 of the shared contract draft (#51, v0.7-draft) also states. The evidence-grade pair follows section 3.3 of the MCP boundary deep dive (#32). A reader built to the v0.7-draft contract has no rule that decides the pair, because that draft treats a service-side receipt as correlation evidence rather than attestation, and `basis.json` says so under `outside`. The runner refuses to run a case with no `basis.json`.

## Signing input

The test service signs five receipt fields: `action_id`, `created_at`, `receipt_id`, `service` and `ticket_id`. Each comes from the receipt span attribute of the same name with the `receipt.` prefix removed, except `receipt_id`, which comes from `receipt.id`. The signing input is those five fields serialized as one JSON object with the keys in ascending order, no whitespace between tokens, and ASCII escapes for any non-ASCII character, encoded as UTF-8. For receipt R-7 in `evidence-grade-pair-verifies` the input is these 126 bytes:

```
{"action_id":"P1","created_at":"2026-09-21T15:00:00Z","receipt_id":"R-7","service":"test-ticket-service","ticket_id":"T-1042"}
```

The signature is Ed25519 over those bytes, carried in `receipt.signature` as standard base64 with padding. The verification key is `trust/test-ticket-service.pub.pem`, a PEM-encoded SubjectPublicKeyInfo holding a raw 32-byte Ed25519 public key. In `evidence-grade-pair-fails` the service signed `"ticket_id":"T-9999"` while the span reports `T-1042`, so the signature does not verify against the input the span describes.

## Readers

The reference reader derives each answer from the records and the test service's public key in the trust directory. The naive reader counts receipt spans and repeats the agent's claim. CI requires the naive reader to fail each case listed as discriminating in run.py, because a case it passes separates nothing.

## Fixtures

The generate.py script rebuilds each fixture from a published seed, and the key it derives signs synthetic receipts only. Ed25519 signatures are deterministic, so a rebuild is byte-identical, and CI checks that. Attribute names are illustrative fixture identities, not proposed OTel attribute names.

## Contributing a case

Copy the TEMPLATE directory and follow its mapping.md. Cases for continuity, calls and retries, and approvals follow the shared contract in [issue #41](https://github.com/aaif/wg-observability-and-traceability/issues/41). The cases here need only the effect and its receipt.
