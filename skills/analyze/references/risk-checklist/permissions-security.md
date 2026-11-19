# Risk checklist: Permissions and security

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Data scope | Data split by company, site, warehouse, seller, customer | Does every read and write query get the scope condition on the server (not trusting screen values), is an ID from another scope blocked |
| Function permission | Admin, approval, settlement functions | Does the server check the permission, not just hide the menu |
| Personal data | Name, phone, address, national ID and the like | Encryption or masking at rest, not exposed in logs, error messages or export files |
| Payment data | Cards, bank accounts | Not storing forbidden items such as card numbers, using only payment-gateway tokens |
| Input validation | User input reaches a query, file path, HTML or command | Binding, escaping, allow lists |
| Secrets | Keys, tokens, connection info | Not in code, config files or logs |
