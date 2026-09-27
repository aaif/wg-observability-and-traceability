# Source mapping: AGENT-OR-SDK-NAME

Copy this directory to `test-kit/contributions/AGENT-OR-SDK-NAME/` and fill it in.

## What emits each fixture field

| Fixture attribute | Where your implementation emits it | Notes |
| --- | --- | --- |
| `conversation.id` | | |
| `turn.id` | | |
| `action.id` | | |
| `receipt.*` | | Emitted by the independent service, never by the agent. |

## Limitations

List every case in `test-kit/cases/` your implementation cannot produce, and why. An unsupported
capability is recorded here; it is never reported as a passing case.

## Your case

A focused example needs only `records.otlp.json` (an OTLP/JSON trace export), `expected.json`
(the answer a correct reader derives from it) and `basis.json` (the document that answer follows:
`answer_follows.document`, `.section` and `.url`). It does not need a complete application.
