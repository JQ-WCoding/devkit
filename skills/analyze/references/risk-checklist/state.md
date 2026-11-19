# Risk checklist: State

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| State transitions | Status codes on orders, payments, work orders, shipments, settlements | Allowed transitions, whether this change adds a transition, in which states edit or cancel is blocked |
| Reversal | Cancel, refund, return, rework | Are all side effects of the original (quantity, amount, history, external notifications) reversed, partial cancellation |
| Closing | Daily or monthly close, settlement or result confirmation | Are paths that change data in a closed period blocked |
