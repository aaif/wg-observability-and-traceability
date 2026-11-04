# Fixture mapping

The records omit a relationship-method field. For these cases, use the
following defaults from [section 4 of the v0.7 draft](https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md#4-relationships).
No other relationship gets a default.

| Link | Method | Fields in these records |
| --- | --- | --- |
| R1, Turn to Conversation | `attribute-reference` | The `invoke_agent` span has `turn.id=T1` and `conversation.id=C1`. |
| R5, Tool execution to Proposed action | `attribute-reference` | `propose_action` and `execute_tool create_ticket` both have `action.id=P1`. |
| R6, Tool execution to External effect | `external-correlation-key` | `execute_tool create_ticket` has `action.id=P1`; the `test-ticket-service` receipt echoes it in `receipt.action_id=P1`. Join and deduplicate on `receipt.id` within the service and tenant scope. |

The original four cases and `effects-ticket-id-changed` contain one agent and
one test service, with no tenant reuse of `P1`. Their tenant scope is absent.
`effects-action-id-reused-in-another-scope` uses the illustrative resource
attribute `tenant.id` to distinguish `tenant-a` from `tenant-b`. Both use `P1`
and receipt ID `R-9`; the query selects `tenant-a`, whose ticket is `T-1042`.
The receipt from `tenant-b` names `T-2088` and must not join or replace it.

`basis.json` supplies the queried action, service and tenant in
`evaluation_context`. The receipt's `service.name` and `receipt.service` must
both match that service. A different service or tenant does not inherit the
mapping. `tenant.id` is a fixture choice, not a proposed OTel field. This is a
correlation case; the receipt signature does not cover the tenant attribute.

For `effect_correlation`, a service receipt establishes a correlated effect
under the v0.7 draft. That conclusion makes no claim about its signature.
For `receipt_signature`, verify the signed fields against the test service's
public key as described in README.md. The agent's
`evidence.externally_verified` attribute is a claim, not a link method or a
verification result.
