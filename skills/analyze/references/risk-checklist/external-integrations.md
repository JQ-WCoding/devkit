# Risk checklist: External integrations

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Failure handling | Calls to payment gateways, carriers, equipment (PLC), ERP, marketplace APIs | Timeout, retry count and interval, state on failure, how a person reprocesses |
| Transaction boundary | External call inside a DB transaction | Does external latency hold DB locks or connections, the case where the external side succeeds and the DB rolls back |
| Unknown result | No response, timeout | How to query the result and reconcile, prevention of duplicate requests |
| Contract | External response fields and code values | Documented source, what happens with an unknown code value |
