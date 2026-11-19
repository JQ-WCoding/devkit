# Common risk checklist

Contents: How to use · Areas

These are the places where incidents recur regardless of the business domain. When an item's **signal** shows up in the change, write the question and answer (evidence `file:line` or `needs confirmation`) under "Risk check" in the analysis doc. Do not write items that do not apply.

## How to use

- Fix the change scope (tables, APIs, screens, batches that change) first, and scan only that scope.
- Scan the [Areas](#areas) index against that scope and read only the area files whose signal appears in the change. Unsure whether an area applies → open its file.
- Answer with the current approach confirmed in code. If `docs/rules/` describes this repo's approach, follow it.
- If you cannot answer, do not guess; raise it as `needs confirmation` and ask at the 🛑 gate.

## Areas

| Area | Signals (short) | File |
|---|---|---|
| Data and transactions | one request writes 2+ tables or stores; derived values (totals, balances, stock, results); delete or cancel; UPDATE/DELETE with dynamic WHERE | [data-transactions.md](risk-checklist/data-transactions.md) |
| Concurrency and duplicates | shared quantity changed by several users; values that must be unique; webhooks, message consumers, retried batches, double-clickable saves; async ordering; same record edited in two screens | [concurrency-duplicates.md](risk-checklist/concurrency-duplicates.md) |
| State | status codes; cancel, refund, return, rework; daily or monthly close, settlement | [state.md](risk-checklist/state.md) |
| Numbers and time | money, fees, taxes; unit conversion, fractional quantities; date aggregation, cut-off times, time zones; delivery, settlement or validity dates | [numbers-time.md](risk-checklist/numbers-time.md) |
| Permissions and security | data split by company, site, warehouse, seller or customer; admin, approval, settlement functions; personal or payment data; user input reaching a query, path, HTML or command; keys, tokens, connection info | [permissions-security.md](risk-checklist/permissions-security.md) |
| External integrations | calls to payment gateways, carriers, equipment, ERP, marketplace or other external APIs; external call inside a DB transaction; timeouts; external fields and code values | [external-integrations.md](risk-checklist/external-integrations.md) |
| Volume and performance | query or API call per list item; list queries, exports; new query conditions or sorting; uploads, bulk processing, batches | [volume-performance.md](risk-checklist/volume-performance.md) |
| History and operations | changes to amounts, quantities, states, permissions; errors and integration logs; failures recovered by hand | [history-operations.md](risk-checklist/history-operations.md) |
| Deployment and compatibility | column, table, constraint changes; converting existing data; APIs or messages used by other apps; new env vars or config keys; rollback after deploy | [deployment-compatibility.md](risk-checklist/deployment-compatibility.md) |
| Display and errors | code that catches exceptions; new wording; date, number, money display | [display-errors.md](risk-checklist/display-errors.md) |
