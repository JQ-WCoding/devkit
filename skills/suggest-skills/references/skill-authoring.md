# Skill and agent authoring rules

Source: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), plus devkit's own rules. suggest-skills follows this to create a skill or agent and improve-skill follows it to fix one. `check_skill.py` enforces the mechanical limits (name, description, body length, links, `Contents:`, file names, stale phrases), so they are not repeated here.

Contents: Principles · Location and names · Evals first · SKILL.md · Patterns · Scripts · Agents · Improving an existing skill · Check · Pre-share checklist

## Principles

- **Conciseness:** cut what Claude already knows; general knowledge gets a keyword or a name, not an explanation.
- **Degrees of freedom match fragility:** text criteria → parameterized template or script → exact command for destructive, ordered or consistency-critical work (migrations, deletes, DB writes).
- One term per concept; one default plus one exception.
- Test on the target models: Haiku, `model: sonnet` or a low `effort` need explicit steps.

## Location and names

- Repo-only skills go in `<repo>/.claude/skills/<name>/`; agents go in `<repo>/.claude/agents/<name>.md`.
- Never rename an existing skill (other docs link to it). Name the action, verb first, like the rest of the collection (devkit: `suggest-skills`, `clean-temp`, `improve-skill`).
- Look for overlaps in the available skill list first. If one overlaps, don't create a new skill, or say in both descriptions when not to use each.
- Write project skills and agents in the project's document language (the one `docs/rules/` uses).

## Evals first

1. Find the gap. List what the user repeatedly told Claude in this conversation (or described from earlier sessions) and where Claude was wrong or missed something. That is the no-skill baseline.
2. Write at least 3 scenarios for those gaps in `evals/evals.json`. An auto-selected skill also needs 1 request it must not handle.
3. Write minimal instructions: only what closes the gaps.
4. Iterate: run the scenarios in a fresh session, compare against the baseline and refine.

```json
[
  {"skills": ["<name>"], "query": "<real request sentence>", "files": [],
   "expected_behavior": ["<observable expected behavior>"]}
]
```

## SKILL.md

- `description`: what it does, when to use it (the request phrases users actually type) and when not to. Claude picks a skill from this sentence alone.
- Skills that should run only when the user invokes them (delete, deploy, backup, DB writes, checks) get `disable-model-invocation: true`. If the skill takes arguments, add `argument-hint`.
- Body: only this project's paths, rules, judgment criteria and prohibitions. Don't copy rules from `docs/rules/`; link them. Details go to reference files.
- Scope: a skill acts on the project root where Claude was started (the git top-level of the working directory), even when installed globally as a plugin or user skill. It never edits outside that root (`~/.claude`, installed plugin copies, other repos); reading there is limited to other skills' names and descriptions for an overlap check. When a target lies outside, it says so and stops.
- Multi-step work: numbered steps, 🛑 user approval points, verify → fix → re-verify; a long workflow adds a `Progress:` checklist Claude copies and ticks off.
- Time-sensitive facts: current method only, marked `checked scope (YYYY-MM-DD)` or with what to do when the fact fails; superseded methods under `## Old patterns` in a collapsed `<details>` block.
- Generalize. Skill files contain no customer names, personal data, secrets or raw quotes from transcripts.
- Human installation steps go in `SETUP.md`.

## Patterns

When they fit: template (strict for machine-read or fixed formats such as data files, commit or PR bodies; flexible otherwise) · 2–3 input → output examples for style · conditional workflow (a large branch → its own reference file) · plan → validate → execute for batch or destructive work (plan file in the scratchpad; a validating script prints specific errors).

## Scripts

- Put deterministic work in `scripts/`. For each script, SKILL.md says whether to run it ("Run `x.py`") or read it ("See `x.py` for <the algorithm>").
- Scripts: own error handling that prints the next action, justified constants, `python3 -I`, stdlib first.
- List required packages and CLIs in SKILL.md, with install steps in `SETUP.md`. Don't assume anything is installed.
- Refer to MCP tools by their full name; in Claude Code that is `mcp__<server>__<tool>`. Use the names actually visible in the session, since they differ per person.
- Don't pile run results, backups or downloads into the skill folder. Temp files go in the scratchpad.

## Agents

- Frontmatter: `name`, `description` (what + when), `model: inherit`, and `tools`. Tools are read-only: `Read, Grep, Glob`, plus `Bash` and full names of read-only MCP tools if needed.
- `effort`: an agent that reads or runs and then summarizes pins `effort: low`. An agent whose output is a judgment omits `effort`, so it follows the session.
- Body: the assigned scope, "does not modify files", the report format, confirmed findings kept apart from guesses, and a plain statement when something was not found.

## Improving an existing skill

improve-skill works from this section. The session that edits a skill (Claude A) never judges it. A fresh session with the skill loaded (Claude B) runs real requests, and its behavior is the evidence: the corrections the user gave after it ran, and how it navigated the files (which ones it read, in what order).

| Observation | Likely fix |
|---|---|
| The skill states a rule but Claude B broke it (repeated correction) | Make the rule prominent: move it into the step where it applies, word it as "MUST", or turn it into a checklist item or a script check |
| The user keeps supplying a rule the skill lacks | Add the minimal rule, generalized |
| Wrong skill picked, or not picked | Fix the `description`: key terms, request phrases, when not to use it |
| Files read in an unexpected order | Reorder SKILL.md so the navigation matches the work |
| A needed file was not read (missed link) | Link it explicitly at the step that needs it and say when to read it |
| One reference file re-read on every run | Move that content into SKILL.md |
| A bundled file is never read | Remove it, or point to it at the step that needs it |

- One fix per observed gap. Keep the diff minimal and add an eval scenario that reproduces the gap. Then re-run `check_skill.py` and have the scenarios run in a new session.

## Check

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/scripts/check_skill.py" <skill folder> [...]
```

- Fix `ERROR`s. Review `WARN`s and note in the report any reason to keep one. Then go through the Pre-share checklist by hand.
- Don't judge eval scenarios in the session that wrote the skill. Tell the user to enter each `query` in a new session and compare.

## Pre-share checklist

```
- [ ] description: what + when (request phrases) + when not
- [ ] Principles followed; risky steps have exact commands and a 🛑 approval point
- [ ] Names consistent with the collection
- [ ] Multi-step work: numbered steps, progress checklist, verify → fix → re-verify
- [ ] Scripts: errors handled, constants justified, run-vs-read stated, packages listed
- [ ] MCP tools by full name
- [ ] No customer names, personal data, secrets or raw transcript quotes
- [ ] Acts only on the project root (git top-level of the working directory), even when installed globally
- [ ] ≥3 evals (+1 must-not-handle if auto-selected), compared to the no-skill baseline in a new session on the target model(s)
- [ ] check_skill.py: no ERROR; WARNs reviewed
```
