# Common risk checklist

Contents: How to use · Data and transactions · Concurrency and duplicates · State · Numbers and time · Permissions and security · External integrations · Volume and performance · History and operations · Deployment and compatibility · Display and errors

These are the places where incidents recur regardless of the business domain. When an item's **signal** shows up in the change, write the question and answer (evidence `file:line` or `needs confirmation`) under "Risk check" in the analysis doc. Do not write items that do not apply.

## How to use

- Fix the change scope (tables, APIs, screens, batches that change) first, and scan only that scope.
- Answer with the current approach confirmed in code. If `docs/rules/` describes this repo's approach, follow it.
- If you cannot answer, do not guess; raise it as `needs confirmation` and ask at the 🛑 gate.

## Data and transactions

| Item | Signal | What to check |
|---|---|---|
| Atomicity | One request changes two or more tables or stores | Is it one transaction, what is left after a mid-way failure, are non-rollbackable side effects (files, messages, external calls) deferred until after commit |
| Consistency rules | Values derived from others: totals, balances, stock, production results | Paths where derived values and sources can diverge, how to recalculate or reconcile |
| Deletion | Delete or cancel features | Logical or physical delete, what happens to referencing data |
| Empty condition | UPDATE/DELETE with dynamic WHERE or filters | Does an empty condition change everything |

## Concurrency and duplicates

| Item | Signal | What to check |
|---|---|---|
| Shared quantity | Several users change stock, seats, balances, coupon counts or equipment capacity at once | Locking (row lock, reservation) or version comparison, prevention of negative or over-allocation |
| Uniqueness | Several requests register a value that must be unique (one reservation per target per day, order number, member email) | Is there a DB unique constraint (check-then-insert alone fails under concurrent requests), is the violation turned into a user error (distinguished by constraint name), cleanup of existing duplicates |
| Idempotency | Payment notifications, webhooks, message consumers, retried batches, double-clickable saves | Is the same request applied once even if it arrives twice (idempotency key, processed-state check) |
| Ordering | Async events and messages | What happens if they arrive out of order |
| Concurrent edits | The same document or order edited in two screens | Does a later save overwrite an earlier one |

## State

| Item | Signal | What to check |
|---|---|---|
| State transitions | Status codes on orders, payments, work orders, shipments, settlements | Allowed transitions, whether this change adds a transition, in which states edit or cancel is blocked |
| Reversal | Cancel, refund, return, rework | Are all side effects of the original (quantity, amount, history, external notifications) reversed, partial cancellation |
| Closing | Daily or monthly close, settlement or result confirmation | Are paths that change data in a closed period blocked |

## Numbers and time

| Item | Signal | What to check |
|---|---|---|
| Money | Prices, payments, fees, taxes, settlements | Integers or fixed decimals instead of floating point, where and how rounding happens, currency, difference between the total and the sum of items |
| Quantity and units | Unit conversion (box↔piece, kg↔g), fractional quantities | Source of the conversion basis, accumulated conversion error |
| Time zone | Date-based aggregation, cut-off times, overseas users or servers | Stored time zone, displayed time zone, what "today" means |
| Business days | Delivery dates, settlement dates, validity periods | Holidays and weekends, whether boundary days are included |

## Permissions and security

| Item | Signal | What to check |
|---|---|---|
| Data scope | Data split by company, site, warehouse, seller, customer | Does every read and write query get the scope condition on the server (not trusting screen values), is an ID from another scope blocked |
| Function permission | Admin, approval, settlement functions | Does the server check the permission, not just hide the menu |
| Personal data | Name, phone, address, national ID and the like | Encryption or masking at rest, not exposed in logs, error messages or export files |
| Payment data | Cards, bank accounts | Not storing forbidden items such as card numbers, using only payment-gateway tokens |
| Input validation | User input reaches a query, file path, HTML or command | Binding, escaping, allow lists |
| Secrets | Keys, tokens, connection info | Not in code, config files or logs |

## External integrations

| Item | Signal | What to check |
|---|---|---|
| Failure handling | Calls to payment gateways, carriers, equipment (PLC), ERP, marketplace APIs | Timeout, retry count and interval, state on failure, how a person reprocesses |
| Transaction boundary | External call inside a DB transaction | Does external latency hold DB locks or connections, the case where the external side succeeds and the DB rolls back |
| Unknown result | No response, timeout | How to query the result and reconcile, prevention of duplicate requests |
| Contract | External response fields and code values | Documented source, what happens with an unknown code value |

## Volume and performance

| Item | Signal | What to check |
|---|---|---|
| Calls in a loop | Querying or calling an API per list item | Can it be batched, expected count × time per item |
| Paging | List queries, exports | Page size limit, cost of the total-count query |
| Indexes | New query conditions or sorting | Indexes on condition columns, whether an execution plan check is needed |
| Time limits | Uploads, bulk processing, batches | Transaction, request and proxy time limits vs expected duration |

## History and operations

| Item | Signal | What to check |
|---|---|---|
| Audit history | Changes to amounts, quantities, states, permissions | Is who changed what and when recorded |
| Logs | Errors, external integrations | Do logs carry a key to trace the cause (request ID, order number), are sensitive values left out |
| Operational response | Failures are recovered by hand | Reprocessing screen or script, alerts |

## Deployment and compatibility

| Item | Signal | What to check |
|---|---|---|
| Schema change | Column, table, constraint changes | Does old code run on the new schema and new code on the old schema (add → migrate → remove), change and rollback SQL, does the app apply the schema at startup (then a failed constraint creation is a failed boot), is a baseline such as `IF NOT EXISTS` actually applied to existing DBs, if there are several DB vendors were all updated |
| Data migration | Converting existing data | Row count, duration, re-runnable, how to revert |
| API compatibility | APIs or messages called by other apps or externals | Adding fields is compatible; removal, renaming or meaning changes need a caller check |
| Config | New environment variables or config keys | Is there a value in every environment (local, dev, prod), default value |
| Rollback | Problems after deployment | Is reverting the code enough, or must data and schema be reverted too |

## Display and errors

| Item | Signal | What to check |
|---|---|---|
| Error handling | Code that catches exceptions | Does it hide failure as success, are the user message and the log separated |
| Localization | New wording | Do message keys and translation follow the repo rules |
| Formatting | Date, number, money display | Are display format and storage format kept apart |
