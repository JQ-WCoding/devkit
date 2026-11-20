# Common risk checklist

Scan only the change scope (tables, APIs, screens, batches that change) against each area's signals; for an area that applies, check its items. Answer from code (`file:line`); a repo approach in `docs/rules/` wins. Items are names; ⚠ marks a trap to check explicitly.

**Data and transactions** — one request writes 2+ tables or stores; derived values (totals, balances, stock, results); delete or cancel; UPDATE/DELETE with dynamic WHERE
- Atomicity (side effects after commit) · derived-value consistency and reconcile path · logical vs physical delete
- ⚠ Empty condition: an empty dynamic WHERE or filter changes every row

**Concurrency and duplicates** — shared quantity changed by several users; values that must be unique; webhooks, message consumers, retried batches, double-clickable saves; async ordering; same record edited in two screens
- Shared-quantity locking · idempotency · ordering · lost update
- ⚠ Uniqueness: a DB unique constraint (check-then-insert alone fails under concurrency); violation → user error by constraint name; existing duplicates

**State** — status codes; cancel, refund, return, rework; daily or monthly close, settlement
- Allowed transitions · full reversal of side effects, partial cancel · closed-period writes

**Numbers and time** — money, fees, taxes; unit conversion, fractional quantities; date aggregation, cut-off times, time zones; delivery, settlement or validity dates
- Money precision and rounding · unit conversion · time zone and "today" · business days and boundaries

**Permissions and security** — data split by company, site, warehouse, seller or customer; admin, approval, settlement functions; personal or payment data; user input reaching a query, path, HTML or command; keys, tokens, connection info
- Server-side data scope · server-side function permission · personal data · payment data · input validation · secrets

**External integrations** — calls to payment gateways, carriers, equipment (PLC), ERP, marketplace or other external APIs; external call inside a DB transaction; timeouts; external fields and code values
- Failure and reprocessing · external call inside a transaction · unknown result and reconcile · contract and unknown codes

**Volume and performance** — query or API call per list item; list queries, exports; new query conditions or sorting; uploads, bulk processing, batches
- N+1 · paging and count cost · indexes · timeouts vs duration

**History and operations** — changes to amounts, quantities, states, permissions; errors and integration logs; failures recovered by hand
- Audit history · traceable logs without sensitive values · reprocessing and alerts

**Deployment and compatibility** — column, table, constraint changes; converting existing data; APIs or messages used by other apps; new env vars or config keys; rollback after deploy
- Data migration · API compatibility · config in every environment · rollback scope
- ⚠ Schema change: old code on new schema and new on old (expand/contract); change and rollback SQL; if the app applies the schema at startup, a failed constraint is a failed boot; is a baseline such as `IF NOT EXISTS` actually applied to existing DBs; every DB vendor updated

**Display and errors** — code that catches exceptions; new wording; date, number, money display
- Failure hidden as success · message keys · display vs storage format
