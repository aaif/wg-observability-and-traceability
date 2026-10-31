# Source mapping: AGENT-OR-SDK-NAME

Copy this file to `test-kit/contributions/AGENT-OR-SDK-NAME/mapping.md` and fill it in. The `contributions/` directory holds mappings only. The runner never reads it, and it refuses to run if a fixture file sits there. Executable examples go under `test-kit/cases/AGENT-OR-SDK-NAME-CASE/`, as described in "Your case" below.

## What emits each fixture field

| Fixture attribute | Where your implementation emits it | Notes |
| --- | --- | --- |
| `conversation.id` | | |
| `turn.id` | | |
| `action.id` | | |
| `receipt.*` | | Emitted by the independent service, never by the agent. |

## Relationship methods

Name the exported method for each link the case uses. If the records omit
the method, declare the default here for that link alone. Do not infer a
method from matching values without either declaration.

| Link | Method | Fields or span links that establish it | Issuing scope |
| --- | --- | --- | --- |
| R1, Turn to Conversation | | | |
| R5, Tool execution to Proposed action | | | |
| R6, Tool execution to External effect | | | |

## Limitations

List every case in `test-kit/cases/` your implementation cannot produce, and why. An unsupported
capability is recorded here; it is never reported as a passing case.

## Your case

A focused example needs only `records.otlp.json` (an OTLP/JSON trace export),
`expected.json` (the answer a correct reader derives from it) and `basis.json`
(the rule, checks and `evaluation_context`: action, service and tenant).
Keep the expected answer outside the reader's input. The example does not
need a complete application.

Put these three files in `test-kit/cases/AGENT-OR-SDK-NAME-CASE/`, then check them with:

```sh
python3 test-kit/run.py
```

The runner discovers every directory under `test-kit/cases/`. A wrong
`expected.json` prints `DIFF AGENT-OR-SDK-NAME-CASE` and exits 1. A fixture file
under `contributions/` stops the run with exit 2, so no example goes unchecked.
