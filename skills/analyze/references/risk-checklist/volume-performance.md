# Risk checklist: Volume and performance

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Calls in a loop | Querying or calling an API per list item | Can it be batched, expected count × time per item |
| Paging | List queries, exports | Page size limit, cost of the total-count query |
| Indexes | New query conditions or sorting | Indexes on condition columns, whether an execution plan check is needed |
| Time limits | Uploads, bulk processing, batches | Transaction, request and proxy time limits vs expected duration |
