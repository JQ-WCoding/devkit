# Go design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Small interfaces at the consumer | A large interface defined next to its only implementation | Define a small interface where it is used |
| Errors as values | Ignored errors (`_ =`), `panic` for expected failures, lost context | Return and wrap with `%w` |
| Composition | Struct embedding used to fake inheritance | Explicit fields or small interfaces |
| Context | Blocking calls or goroutines without `context.Context` | Pass the caller's context |
| Package boundaries | `util`/`common` packages growing; import cycles worked around | Package by what it provides |
