---
name: suggest-skills
description: Propose repo-specific rule rows, skills and agents from code pinpoints, fix commits, repeated tasks and repeated corrections; build only the chosen ones. Use for "suggest skills", "find rules to add", "make this a skill".
argument-hint: "[rules | skills | all] [--since YYYY-MM-DD]"
---

# Suggest rules, skills and agents

**No suggestion without evidence.** Evidence is the target repo's `file:line`, commits and fingerprint numbers, tasks repeated in this conversation, and corrections the user gave. Do not carry over rules seen in other projects.

| Reference | When |
|---|---|
| [catalog.md](references/catalog.md) | What to suggest under which conditions |
| [pinpoint-checklist.md](references/pinpoint-checklist.md) | Finding rule row candidates — also pass its path to subagents |
| [skill-authoring.md](references/skill-authoring.md) | When building a chosen skill or agent |
| Blueprints: [project-flow](references/blueprints/project-flow.md) · [db-analyst](references/blueprints/db-analyst.md) · [knowledge-reader](references/blueprints/knowledge-reader.md) · [spec-analyst](references/blueprints/spec-analyst.md) · [workspace-cleanup](references/blueprints/workspace-cleanup.md) · [visual-docs](references/blueprints/visual-docs.md) · [tool-skill](references/blueprints/tool-skill.md) | Read only the ones you decide to build |

Argument: `rules` for rule rows only, `skills` for skills and agents only, none for both.

Baseline (`--since`): argument → last commit date of `docs/rules/` (`git log -1 --format=%ad --date=short -- docs/rules`) → full history (also when `docs/rules/` was just created and has no commit). If fewer than 20 commits follow the baseline, widen to the previous rules commit date, and if still too few, to full history. The baseline **only narrows new fix candidates**; "does the same mistake recur" is always counted on full history.

## 0. Check the target

- If `docs/rules/` is missing, suggest running `devkit:setup` first. If the user says go ahead anyway, only make suggestions and leave rule rows in the report.
- Read existing project skills and agents (`.claude/skills/` and `.claude/agents/` listings with each description), `CLAUDE.md` (its "Project skills and agents" section, or the whole file if absent), and user-level and other plugins' skill lists to avoid overlapping suggestions. Skills with `disable-model-invocation` do not show in the list, so look at the folders directly.

## 1. Gather evidence

**Fingerprint** (script to run):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/scan_repo.py" <repo root> [--since <baseline>] --out <scratchpad>/fingerprint.json > <scratchpad>/fingerprint.md
```

**Rule row candidates** (`rules` or both):

- Launch one `devkit:code-reader` per layer (subproject, DB, infra) **concurrently in one message** (effort lower). Inside a subproject, also launch separate ones for a sub-app where fix hotspots cluster or a path the rules docs call "separate". In a small repo (fewer than 200 source files and at most 2 layers) the main agent does it directly.
- Put in the brief: the assigned path; the fingerprint lines for that path (internal modules, calls, path shapes, warning comments, fix commits — only those for the path); the path of the matching `docs/rules/<layer>.md` with "read it yourself and drop rows that already exist"; the absolute path of [pinpoint-checklist.md](references/pinpoint-checklist.md) (`${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/references/pinpoint-checklist.md`) with "follow its adoption criteria, per-area questions and candidate format"; "return only the candidate table — `confirmed` rows first, up to 15 rows"; "read only the fix commits for your path".
- If the fingerprint's "Top extensions" lists non-source extensions (report layouts, schemas, templates), name that side feature separately in the brief. Missing it drops that whole section.
- Even S1 and S3 rows a subagent marked `confirmed` are checked by the main agent against the evidence file or `git show` before writing them into docs (subagents sometimes misread a commit's nature).
- Fix commits spanning several layers are read by the main agent with `git show` to judge "could the same mistake happen again in another file". Fixes in archive or old template folders (`archive`, `old`, `deprecated` etc.) are not used as evidence.

**Skill and agent candidates** (`skills` or both): match the conditions in [catalog.md](references/catalog.md) against the fingerprint and history. Reading a blueprint to judge fit is fine. Find repeated tasks in groups of same-type commits (same scope, same verb, same folder pattern), traces of repeating the same steps in this conversation, and repeated tasks the user mentioned.

**Corrections**: if the user made the same correction twice or more in this conversation, raise it as a rule row or skill content candidate.

Save the raw tables returned by subagents to `<scratchpad>/candidates.md`, and the main agent's merged verdicts to `<scratchpad>/suggestions.md` (adopted candidates, `needs confirmation`, discarded with reasons).

## 🛑 Proposal table

Show one table and let the user choose (AskUserQuestion multiSelect, up to 4 per question).

| Kind | Name / target | Why (one-phrase evidence) | What gets built | Recommended |
|---|---|---|---|---|

- At most 3 recommended; the rest go on one line each as "next candidates".
- For rule rows, show the count per target doc and 2–3 representative rows (the full set is in `suggestions.md`).
- If a rule row needs a layer doc that does not exist yet, ask separately with a single choice: "new doc / section of an existing doc".
- If you found places where existing rules and code disagree, report only the difference, taking code as the reference. Do not silently change rules.

## 2. Build (chosen items only)

- **Rule rows**: add to the matching `docs/rules/<layer>.md` in the existing style. If the layer doc is missing, create it from the setup layer doc skeleton and add one line each to the `docs/rules/README.md` index and the `CLAUDE.md` table.
- **Agents**: write the blueprint skeleton to `.claude/agents/<name>.md`. Fill `{{…}}` from evidence and delete lines without evidence. Use the DB MCP tool names actually visible in this session.
- **Skills**: build under `.claude/skills/<name>/` following [skill-authoring.md](references/skill-authoring.md) — at least 3 eval scenarios, rules as links to `docs/rules/`, scripts run with `python3 -I`.
- If you built a skill or agent, add one line each (what it is and when to use it) to the "Project skills and agents" section of `CLAUDE.md`.
- Only append to existing files with Edit and preserve line endings. Do not commit.

## 3. Check

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/check_docs.py" <repo root>
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/scripts/check_skill.py" <repo root>/.claude/skills/<built skill>
```

Run `check_skill.py` only when you built a skill. Fix `ERROR`s and run again. Do not judge eval scenarios in this session; tell the user to confirm with a representative request in a new session.

## 4. Report

Report what was built and its files, candidates not chosen (to revisit), check results, what could not be verified, and the next baseline (today's date and last commit hash).
