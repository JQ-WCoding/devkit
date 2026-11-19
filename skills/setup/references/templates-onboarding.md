# Onboarding guide template

Read only when the onboarding guide was approved at 🛑B. Slots and fixed sentences follow "How to use" in [templates.md](templates.md).

Create it only when there are 3+ environment setup steps or external dependencies such as VPN, tunnels or company accounts (confirm at 🛑B). Write a step doc when README or scripts give evidence for its content; for a step with no evidence, put only its name in the table marked `needs confirmation` (never invent install commands).

Step doc `docs/guide/0N-<topic>.md`: title → `[Onboarding](developer-onboarding.md)` link → what to do (numbered steps or a table, only commands with evidence) → done when → `Checked: date · unverified scope`.

```markdown
# {{project name}} developer onboarding

{{version}} · {{YYYY-MM-DD}} · for internal developers

**Goal:** {{one sentence on what you can do after onboarding}}

**Get before starting:** {{list of permissions, accounts and keys — items only, not values}}

| Step | Doc | Done when |
|---|---|---|
| 1 | [{{step}}]({{0N-file}}.md) | {{a result you can see}} |

**Daily:** {{one line of the daily start order → shut down in reverse}}

- Use credentials delivered to you individually and never record them in Git.
- {{checked date, OS checked and unverified scope}}
- During development, follow the [development rules](../rules/README.md).
```

Korean fixed sentences (use verbatim when the document language is Korean):

```markdown
- 인증값은 개별 전달받은 값을 쓰고 Git에 기록하지 않는다.
- 개발 중에는 [개발 규칙](../rules/README.md)을 따른다.
```
