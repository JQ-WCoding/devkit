# Risk checklist: Data and transactions

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Atomicity | One request changes two or more tables or stores | Is it one transaction, what is left after a mid-way failure, are non-rollbackable side effects (files, messages, external calls) deferred until after commit |
| Consistency rules | Values derived from others: totals, balances, stock, production results | Paths where derived values and sources can diverge, how to recalculate or reconcile |
| Deletion | Delete or cancel features | Logical or physical delete, what happens to referencing data |
| Empty condition | UPDATE/DELETE with dynamic WHERE or filters | Does an empty condition change everything |
