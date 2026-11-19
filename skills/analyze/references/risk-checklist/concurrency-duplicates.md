# Risk checklist: Concurrency and duplicates

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Shared quantity | Several users change stock, seats, balances, coupon counts or equipment capacity at once | Locking (row lock, reservation) or version comparison, prevention of negative or over-allocation |
| Uniqueness | Several requests register a value that must be unique (one reservation per target per day, order number, member email) | Is there a DB unique constraint (check-then-insert alone fails under concurrent requests), is the violation turned into a user error (distinguished by constraint name), cleanup of existing duplicates |
| Idempotency | Payment notifications, webhooks, message consumers, retried batches, double-clickable saves | Is the same request applied once even if it arrives twice (idempotency key, processed-state check) |
| Ordering | Async events and messages | What happens if they arrive out of order |
| Concurrent edits | The same document or order edited in two screens | Does a later save overwrite an earlier one |
