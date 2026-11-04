# Skill and agent authoring principles

Source: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Location and name

- Repo-only: `<repo>/.claude/skills/<name>/`; agents: `<repo>/.claude/agents/<name>.md`.
- `name`: at most 64 chars of lowercase letters, digits and hyphens, no `claude` or `anthropic`, same as the folder name. Do not rename after creation (other docs link to it).
- Look for overlaps in the available skill list first. If one overlaps, don't create a new one, or state in both descriptions when not to use each.
- Write project skills and agents in the project's document language (the one `docs/rules/` uses).

## Eval scenarios first

- First write down what the user repeatedly told you in this conversation and where Claude was wrong or missed something. Put only what fills that gap into the skill.
- Keep 3+ scenarios in `evals/evals.json`. For auto-selected skills include 1 "request this skill must not handle".

```json
[
  {"skills": ["<name>"], "query": "<real request sentence>", "files": [],
   "expected_behavior": ["<observable expected behavior>"]}
]
```

## SKILL.md

- `description`: what it does + when to use it (the request phrases users actually type) + when not to. Third person, at most 1,024 chars, no XML tags. Skill selection is decided by this sentence alone.
- Skills to run only when the user invokes them (delete, deploy, backup, DB writes, checks): `disable-model-invocation: true`. If it takes arguments: `argument-hint`.
- Body: only this project's paths, rules, judgment criteria and prohibitions. Do not duplicate rules in `docs/rules/`; link them.
- Under 500 lines. When it grows, move details to reference files. Link reference files one level deep from SKILL.md, and put a `Contents:` line under the title when one exceeds 100 lines.
- For tasks where order and precision matter, write the commands verbatim. For judgment tasks, give only the criteria.
- With many steps, use numbered steps with user approval points (🛑) and a verify → fix → re-verify loop.
- Options: one default and one exception. Use one term per concept.
- Put human installation instructions in `SETUP.md`.
- Instead of sentences that go stale, write `checked scope (YYYY-MM-DD)` or what to do when it fails.

## Scripts

- Put deterministic work in `scripts/` and say in SKILL.md whether to run or read each. Let scripts handle errors and tell the next action. Comment constants with their rationale. Run Python with `python3 -I`.
- Do not pile run results, backups or downloads into the skill folder. Temp files go in the scratchpad.

## Agents

- Frontmatter: `name`, `description` (what + when), `model: sonnet`, `tools` (read-only only: `Read, Grep, Glob`, plus `Bash` and full names of read-only MCP tools if needed).
- Body: assigned scope, "does not modify files", report format, separation of confirmed and guessed, saying plainly when something was not found.

## Check

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/scripts/check_skill.py" <skill folder> [...]
```

- Fix `ERROR`s; review `WARN`s and note in the report if there is a reason to keep them.
- What the script cannot see: whether the description alone tells when to use it, whether known explanations remain, whether risky tasks have a confirmation step.
- Do not judge eval scenarios in the same session. Tell the user to compare by entering the `query` in a new session.
