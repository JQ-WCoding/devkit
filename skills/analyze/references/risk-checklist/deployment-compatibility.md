# Risk checklist: Deployment and compatibility

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Schema change | Column, table, constraint changes | Does old code run on the new schema and new code on the old schema (add → migrate → remove), change and rollback SQL, does the app apply the schema at startup (then a failed constraint creation is a failed boot), is a baseline such as `IF NOT EXISTS` actually applied to existing DBs, if there are several DB vendors were all updated |
| Data migration | Converting existing data | Row count, duration, re-runnable, how to revert |
| API compatibility | APIs or messages called by other apps or externals | Adding fields is compatible; removal, renaming or meaning changes need a caller check |
| Config | New environment variables or config keys | Is there a value in every environment (local, dev, prod), default value |
| Rollback | Problems after deployment | Is reverting the code enough, or must data and schema be reverted too |
