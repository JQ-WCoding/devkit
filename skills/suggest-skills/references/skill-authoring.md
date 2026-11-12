# Skill and agent authoring rules

Source: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), plus devkit's own rules. suggest-skills follows this to create a skill or agent and improve-skill follows it to fix one.

Contents: Principles · Location and names · Evals first · SKILL.md · Patterns · Scripts · Agents · Improving an existing skill · Check · Pre-share checklist

## Principles

- **Conciseness.** Claude is already capable. Ask of every line: "Does Claude need this?" and "Does it justify its tokens?" Cut definitions, background and how-tos for well-known tools.
- **Degrees of freedom.** Match how specific you are to how fragile the task is:
  - High (text criteria): several approaches are valid and context decides, e.g. review or analysis.
  - Medium (a template or a script with parameters): a preferred pattern exists and some variation is fine.
  - Low (an exact command, "run exactly this, add no flags"): the task is fragile or destructive, consistency is critical, or the order is fixed, e.g. migrations, deletes or DB writes.
- One term per concept. Give one default plus one exception instead of a menu of options.
- Test with the models the skill will run on. A smaller model (Haiku, or an agent set to `model: sonnet`) needs explicit steps; Opus needs less explanation.

## Location and names

- Repo-only skills go in `<repo>/.claude/skills/<name>/`; agents go in `<repo>/.claude/agents/<name>.md`.
- `name`: at most 64 lowercase letters, digits and hyphens. It must not contain `claude` or `anthropic` and must match the folder name. Don't rename a skill once it exists (other docs link to it).
- Name the action, verb first, in the same pattern as the rest of the collection (devkit: `suggest-skills`, `clean-temp`, `improve-skill`). Avoid vague or generic names (`helper`, `utils`, `tools`, `documents`, `data`, `files`).
- Look for overlaps in the available skill list first. If one overlaps, don't create a new skill, or say in both descriptions when not to use each.
- Write project skills and agents in the project's document language (the one `docs/rules/` uses).
- Name files by what they hold, grouped by domain (`reference/finance.md`, `form_validation_rules.md`), not `doc2.md` or `file1.md`. Use forward slashes in every path.

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

- `description`: what it does, when to use it (the request phrases users actually type) and when not to. Use specific key terms, third person, at most 1,024 chars and no XML tags. Claude picks a skill from this sentence alone.
- Skills that should run only when the user invokes them (delete, deploy, backup, DB writes, checks) get `disable-model-invocation: true`. If the skill takes arguments, add `argument-hint`.
- Body: only this project's paths, rules, judgment criteria and prohibitions. Don't copy rules from `docs/rules/`; link them.
- Scope: a skill acts on the project root where Claude was started (the git top-level of the working directory), even when installed globally as a plugin or user skill. It never edits outside that root (`~/.claude`, installed plugin copies, other repos); reading there is limited to other skills' names and descriptions for an overlap check. When a target lies outside, it says so and stops.
- Keep the body under 500 lines and move details to reference files. Link every reference file directly from SKILL.md (one level deep). A file over 100 lines gets a `Contents:` line under its title.
- Multi-step work gets numbered steps with 🛑 user approval points and a verify → fix → re-verify loop ("continue only once the check passes"). For long workflows, add a progress checklist that Claude copies into its reply and ticks off:
  ```
  Progress:
  - [ ] 1. <step>
  - [ ] 2. <step>
  ```
- Time-sensitive information: don't write date-conditional instructions. Write the current method only. Mark facts with `checked scope (YYYY-MM-DD)` or say what to do when the fact fails. Superseded methods go under `## Old patterns` at the end, in a collapsed `<details>` block.
- Generalize. Skill files contain no customer names, personal data, secrets or raw quotes from transcripts.
- Human installation steps go in `SETUP.md`.

## Patterns

Use these when they fit.

- **Template.** Strict ("use exactly this structure") for output that a machine reads or a format that is fixed: data files, commit or PR bodies. Flexible ("a sensible default; adapt the sections") when judgment helps.
- **Examples.** When output style matters, give 2–3 concrete input → output pairs instead of describing the style.
- **Conditional workflow.** Branch at the decision point ("New content? → Creation steps. Existing content? → Editing steps."). If a branch gets large, move it to its own reference file and say when to read it.
- **Plan → validate → execute.** Use this for batch, destructive or high-stakes work. Claude writes a plan file in the scratchpad (e.g. `changes.json`). A script validates it and prints specific errors (what is wrong and which values are valid). Only then execute, then verify.

## Scripts

- Put deterministic work in `scripts/`. For each script, SKILL.md says whether to run it ("Run `x.py`") or read it ("See `x.py` for <the algorithm>").
- Scripts handle their own errors instead of leaving them to Claude, and print the next action. Comment every constant with its rationale (no magic numbers). Run Python with `python3 -I` and prefer the stdlib.
- List required packages and CLIs in SKILL.md, with install steps in `SETUP.md`. Don't assume anything is installed.
- Refer to MCP tools by their full name; in Claude Code that is `mcp__<server>__<tool>`. Use the names actually visible in the session, since they differ per person.
- Don't pile run results, backups or downloads into the skill folder. Temp files go in the scratchpad.

## Agents

- Frontmatter: `name`, `description` (what + when), `model: sonnet`, and `tools`. Tools are read-only: `Read, Grep, Glob`, plus `Bash` and full names of read-only MCP tools if needed.
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

- Fix `ERROR`s. Review `WARN`s and note in the report any reason to keep one.
- The script checks:
  - frontmatter limits, name matches folder, vague names
  - description length, first/second person, XML tags
  - body length, broken links, references one level deep, `Contents:` in long files
  - non-descriptive file names, bare MCP tool names (unambiguous forms only), backslash paths, phrases that go stale
  - large or archive files, `evals.json` format and count
- Check by hand:
  - the description alone tells when to use the skill
  - conciseness, and the degree of freedom fits the risk
  - risky steps have a 🛑 confirmation
  - names are consistent with the collection
  - required packages are listed
  - no customer or personal data
- Don't judge eval scenarios in the session that wrote the skill. Tell the user to enter each `query` in a new session and compare.

## Pre-share checklist

```
- [ ] description: what + when (request phrases) + when not; specific key terms; third person
- [ ] Every line passes the conciseness test; nothing Claude already knows
- [ ] Freedom matches fragility; risky steps have exact commands and a 🛑 approval point
- [ ] One term per concept; one default + one exception; concrete examples
- [ ] References one level deep; files over 100 lines have Contents; files named by content
- [ ] No time-sensitive sentences (or under Old patterns)
- [ ] Multi-step work: numbered steps, progress checklist, verify → fix → re-verify
- [ ] Scripts: errors handled, constants justified, run-vs-read stated, packages listed, python3 -I, forward slashes
- [ ] MCP tools by full name
- [ ] No customer names, personal data, secrets or raw transcript quotes
- [ ] Acts only on the project root (git top-level of the working directory), even when installed globally
- [ ] ≥3 evals (+1 must-not-handle if auto-selected), compared to the no-skill baseline in a new session on the target model(s)
- [ ] check_skill.py: no ERROR; WARNs reviewed
```
