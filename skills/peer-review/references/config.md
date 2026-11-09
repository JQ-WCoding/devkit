# peer-review config

`.devkit/peer-review/config.json` — local to the reviewer (excluded from Git with `.devkit/`). Every field is optional; without the file only the generic checks run (whitespace-only reformat, line-ending-only changes, missing blank line after the subject, merge and revert lists).

Build it from `docs/rules/git.md` (branch flow, commit format) and the repo's top-level layout. Copy only what the rules state. A convention you inferred from history but the rules do not state goes in with `"judgment": true`, so the report raises it as "needs checking" rather than a violation.

| Field | Meaning |
|---|---|
| `remote`, `branch` | Shared branch to review (default `origin` and the remote default branch). Usually the integration branch teammates merge into, e.g. `dev` |
| `areas` | `[{name, prefix, scope?, rules?}]`, first match wins. `scope` is the commit scope this area maps to (default = `name`); `rules` lists the `docs/rules/` files a reviewer of this area reads first |
| `default_area` | Area name for paths no prefix matches (default `other`) |
| `subject.pattern` | Regex for the subject line. Named groups `type`, `scope`, `desc` are used when present |
| `subject.types`, `subject.scopes` | Allowed values. `scope_separator` (default `,`) splits multiple scopes |
| `subject.scope_matches_area` | Warn when the scopes differ from the scopes of the changed areas |
| `subject.no_period` | Warn on a trailing period |
| `subject.forbidden_endings` | `[{ending, message, judgment?}]` |
| `body.max_lines`, `body.bullet` | Body line limit and required bullet prefix |
| `forbid_trailers` | Warn on `Co-Authored-By`, `Signed-off-by`, `Generated with` and similar lines |
| `forbidden_paths` | `[{prefix, message, judgment?}]` — paths that must not be committed |
| `no_mix` | `[{areas: [a, b], message, judgment?}]` — areas that must not share a commit |
| `type_path` | `[{type, prefix, message, judgment?}]` — a commit type that should not touch a path |
| `revert_markers` | Extra subject words that mark a revert (besides `Revert`) |
| `brief.summary` | One or two lines on the repo for the reviewer brief (stack, layout) |
| `brief.focus`, `brief.notes` | Repo-specific review points and caveats added to the brief |
| `message_language`, `message_register` | Language and tone of per-developer messages (default: the `docs/rules/` language, polite colleague tone) |

Write each `message` in the rules' language and name the rule doc it rests on, e.g. `"PDA and web mixed in one commit (front.md)"`.

## Example

```json
{
  "branch": "dev",
  "areas": [
    {"name": "web", "prefix": "web/", "rules": ["docs/rules/common.md", "docs/rules/front.md"]},
    {"name": "api", "prefix": "api/", "rules": ["docs/rules/common.md", "docs/rules/back.md"]},
    {"name": "db", "prefix": "db/", "scope": "api", "rules": ["docs/rules/db.md"]}
  ],
  "default_area": "repo",
  "subject": {
    "pattern": "^(?P<type>[a-z]+)\\((?P<scope>[a-z,]+)\\): (?P<desc>.+)$",
    "types": ["feat", "fix", "refactor", "chore", "docs", "test"],
    "scopes": ["web", "api", "repo"],
    "scope_matches_area": true,
    "no_period": true
  },
  "body": {"max_lines": 3, "bullet": "-"},
  "forbid_trailers": true,
  "brief": {
    "summary": "Spring API in api/, React web in web/, SQL migrations in db/.",
    "focus": ["Tenant filter (TENANT_ID) on every query of shared tables"]
  }
}
```
