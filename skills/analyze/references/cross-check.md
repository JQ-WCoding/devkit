# Cross-check mode

Contents: When · Flow · Lane map · Evidence types · Source refs · Lane brief · Comparator brief · Gate and answers · Glossary and premises · Done when · Rules-change gate

Analysts that read different evidence compare their findings; only disagreements reach a human. Agreement between agents that read the same sources is not evidence. `scripts/cross_check.py` enforces the rules below; this file explains them.

## When

- The user asks for it ("cross-check", "교차 검증", "should-be vs as-is"), or analyze offers it once when the input is a `docs/rules` draft or touches a glossary term. Otherwise do not use it.
- Cost: 2–3 lane analysts + 1 comparator per round, at most `max_rounds` (default 3) rounds; rounds 2+ re-run only the items the script lists (`insufficient`, `question`).

## Flow

Folder: `<work>/<task>/cross-check/`. Copy this checklist into your reply.

```
Progress:
- [ ] 1. Items, glossary, lane map → plan.json; export non-repo sources
- [ ] 2. Round n: lanes in parallel → lane-<name>.json
- [ ] 3. Comparator → compare.json
- [ ] 4. cross_check.py check → fix and rerun until exit 0; STOP: no → round n+1 on the listed items
- [ ] 5. 🛑 gate with questions.md; answers → answers.json and the decision log
```

1. Split items as in analyze step 1 and read `docs/rules/glossary.md` if it exists. **Do not trace code yourself before the comparison**: what you read first leaks into the lane briefs.
2. Write `plan.json` and export each non-repo source (ticket, Notion/Drive page, provider doc, minutes) into `sources/<lane>/<file>` with its origin URL on the first line. Lanes have no MCP tools and never fetch. Run read-only queries after confirming the target DB; save query text and result as `sources/<lane>/query-<id>.md`.
3. Round n: launch one `devkit:code-reader` per lane in one message, `effort: "higher"`, with the lane brief. Save each reply's JSON block verbatim to `round-<n>/lane-<name>.json`. Lanes never see each other's files.
4. Launch the comparator (general-purpose subagent) with its brief → save to `round-<n>/compare.json`.
5. Run `python3 -I "<plugin root>/skills/analyze/scripts/cross_check.py" check <cross-check dir> --repo <repo root>`. Exit 1 prints what to fix. On `STOP: no`, run the next round with lanes on the listed items only, each brief carrying a targeted question.
6. Put `results.md` in the analysis doc's requirement summary, `not-rules.md` under "Not turned into rules", and ask `questions.md` at the 🛑 gate, which always stops when it has questions. Only `proceed` items get an implementation plan.

`plan.json`:

```json
{"items": [{"id": "1", "text": "Partial refunds keep the original payment date"}],
 "lanes": [{"name": "intent", "side": "should", "question": "What do the owner's records require?",
            "allow": ["docs/spec/**", "src:intent/*"], "deny": []},
           {"name": "code", "side": "is", "question": "What does the system do today?",
            "allow": ["src/**", "db/**", "query:*"]}],
 "max_rounds": 3}
```

`side` is `should` (what should be) or `is` (what is). 2–3 lanes, at least one of each; allow patterns must not overlap (the script refuses shared prefixes).

## Lane map

Pick the row closest to the task; the third lane is optional.

| Situation | should lane | is lane | Optional third (is) |
|---|---|---|---|
| Business feature / requirement | owner decisions, specs, tickets, glossary | code, schema, read-only data | runtime logs |
| Rules draft (`docs/rules`) | decision records, team agreements, minutes | code and config the rule describes | — |
| External API integration | provider contract / API docs | client code | recorded real responses |
| Report / metric | metric definitions, finance or ops policy | SQL, query results | dashboard output |
| Infra / config | runbook, security baseline | IaC files, read-only config dump | — |
| UI | design doc, mockups | screen captures, front code | — |
| System migration | old system behavior and its docs | new system code | parallel-run output |
| Bug triage | expected behavior per report or spec | code, logs | reproduction run |
| Non-code process | policy, regulation, contract | actual records, procedures | — |

## Evidence types

| Type | Meaning | Allowed in |
|---|---|---|
| `decision` | Locatable statement by whoever owns the requirement: customer, product owner, regulator, contract, provider spec, a human's verbatim answer at the gate | should |
| `agreement` | The team's recorded convention: `docs/rules` row with evidence, ADR, glossary row | should |
| `observed` | Current state: `file:line`, query result, captured response, config dump | is |
| `inference` | Reasoning with no record | both |

What the script enforces:

- An `is` lane cannot cite `decision`/`agreement`; a `should` lane cannot cite `observed` (relabel or move the source).
- A ref outside its lane's patterns (`out-of-lane`), unclassifiable, or pointing at a missing file or line (`unverifiable`) counts as `inference`.
- Without `decision` or `agreement`: only `observed` → `current-state` (a description, never a rule or requirement, listed in `not-rules.md`); only `inference` → `question`. A comparator `match` does not override this.
- `proceed` = comparator `match` + intent evidence. `mismatch`, `insufficient`, `question`, `current-state` go to the gate.
- Gate answers in `answers.json` need the verbatim wording; your reading goes in `interpretation`. Only the verbatim text is a `decision`.
- Convention rows (naming, which shared module to call) may rest on `observed` + `agreement`; behavior and policy need `decision` or `agreement`. Judge which kind a row is at the gate.

## Source refs

| Form | For |
|---|---|
| `path:line` (repo-relative) | code, schema files, `docs/rules`, design docs in the repo |
| `src:<lane>/<file>#<anchor>` | exported non-repo material under `sources/<lane>/` |
| `query:<id>` | `sources/<lane>/query-<id>.md` (query text + result) |
| `run:<record path>` | a `record_run.py` / `run-app` record (repo-relative) |

## Lane brief

Fill `<…>`; keep every prohibition.

```text
You are the "<lane>" lane of a cross-check in <repo root>. Question: <lane question>.
Read ONLY these sources: <allow patterns, with src:/query: files spelled out as cross-check/sources/<lane>/…>.
Never open: <deny patterns>, other lanes' sources, any cross-check/round-* file, the analysis doc.
Do not modify files. Skip your usual CLAUDE.md / docs/rules skim unless they are in your sources. Do not judge whether the system is right; report what your sources say.
Items:
<id. text, one per line; in round 2+, only the listed items, each with its targeted question>
Return exactly one fenced json block and nothing after it:
{"lane": "<lane>", "items": [{"id": "<id>", "claim": "<one line>",
  "sources": [{"ref": "<path:line | src:<lane>/<file>#<anchor> | query:<id> | run:<path>>", "type": "<allowed types>"}]}]}
Allowed types for this lane: <should: decision, agreement, inference | is: observed, inference>.
An item you found nothing for: "sources": [] and claim "no record found".
Done when: every item has a claim and each source a ref of an allowed type; <done-when per item, set by the central session>.
```

## Comparator brief

```text
Compare lane findings item by item for a cross-check in <repo root>.
Read only: <cross-check dir>/plan.json and <cross-check dir>/round-<n>/lane-*.json; open a cited ref only to confirm it says what the claim says.
Do not modify files. Do not add your own findings.
For each item in the lane files: status match (lanes agree), mismatch (they disagree), insufficient (a side has nothing usable);
"should" and "is": one line each from the lanes; for mismatch and insufficient a yes/no question for the owner, e.g. "Is <is> intended, given <should>?".
Return exactly one fenced json block: {"items": [{"id", "status", "should", "is", "question"}]}
```

## Gate and answers

Ask `questions.md` items with AskUserQuestion (yes/no, one line of evidence per side). Write each answer to `answers.json` as `{"item", "verbatim", "interpretation"}` and to the decision log with the same split and a re-check condition, then rerun the check. An answer that settles an item is cited in later rounds as `src:<should lane>/answers.md#<item>` after exporting it.

## Glossary and premises

`docs/rules/glossary.md` in the target repo. analyze and peer-review read it first.

```markdown
## Terms
| Term | Current meaning | Legacy meaning | Evidence | Re-check when |
|---|---|---|---|---|
| ACCT_CD | cost center | account | owner decision 2026-03-02 (ticket #812) | the chart of accounts changes |

## Operating premises
| Premise | Holds where | Evidence | Re-check when |
|---|---|---|---|
| Invoices for region EU are issued by the partner system, not by us | region EU | contract §4.2 | the partner contract is renewed |
```

A row needs evidence of type `decision` or `agreement`; a meaning seen only in code is not a glossary row.

## Done when

Every brief that asks for verification (lane, worker, verifier) states completion as the evidence type that settles it: `executed` (a run record), `decision` (owner source), `observed` (`file:line`). The central session writes it; workers do not redefine it. "Matches the current code" verifies a requirement only when the requirement is to keep current behavior.

Executable premises (statements a run can check: an API call, a screen action, a read-only query) go in the analysis doc's "Executable premises" table. develop executes them before reporting; a premise not executed is `not run`, never assumed true.

## Rules-change gate

When a change touches `docs/rules` (or a glossary):

- Each added or changed row carries its evidence type; behavior and policy rows need `decision` or `agreement`.
- Each prohibition gets a one-line why.
- Report the result of applying the rule to the case that triggered it.
- A human approves the content before merge; pr-publish lists it under "Rules / devkit changes".
