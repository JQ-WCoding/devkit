# HCL (Terraform) design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

Idiom rows only: no Common table, no OOP or SOLID rows. Recommend only when infrastructure code changes.

| Principle | Signal in the change | What to check |
|---|---|---|
| DRY via modules | The same resource block copied across environments | An existing module or `for_each` |
| Separation of environments | Environment values hard-coded in resources | Variables and per-environment tfvars or workspaces |
| Explicit dependencies | Ordering relied on implicitly | References or `depends_on` |
| Pinned versions | Provider or module without version constraints | Pin as the repo does |
