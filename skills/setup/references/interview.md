# Interview items

Ask about work policies code cannot decide and environment facts that need confirmation. Do not ask items the fingerprint already settled (such as document language or commit format where 2/3 or more of the history agrees); write them in the 🛑B setup plan as "per fingerprint". Exception: **always ask about AI attribution regardless of the fingerprint, because it overrides the system's default guidance.** Decide the document language separately from the commit language.

- AskUserQuestion takes up to 4 questions per call. Group them round 1 → round 2 → round 3 → environment check, finishing in 2–4 calls.
- The first option is the recommended value with `(Recommended)` at the end of its label. Use the fingerprint's evidence as the recommendation if there is any, otherwise the default below.
- Write each question so it can be understood alone (include a phrase on what the recommendation is based on).

## Round 1 — structure

| Item | Question | Default | Affects |
|---|---|---|---|
| Sharing scope | How much of the rules goes into Git? | Track only `docs/rules/` (and onboarding); `CLAUDE.md` and `.claude/` stay local; other tracked docs in `docs/` stay as they are | `.gitignore`, README source-of-truth statement |
| Team devkit | Should every teammate use devkit? | No (personal choice). If yes, track `CLAUDE.md` and the attribution setting in `.claude/settings.json` (each teammate still installs devkit); if no, only the attribution setting in `.claude/settings.local.json` | `.claude/settings.json` / `settings.local.json`, `.gitignore` |
| Document language | Which language for the rules docs? (decided separately from the commit language) | The language of README and existing docs. If none, the language used in the conversation | All docs |
| Onboarding | Create an environment setup guide for new teammates? | Yes if there are 3+ setup steps not in README or VPN, tunnels or company accounts are needed; otherwise no (a README link is enough) | `docs/guide/` |

## Round 2 — work policies

| Item | Question | Default | Affects |
|---|---|---|---|
| Server start | May Claude start and stop the API and web servers? | No, the developer starts them in the IDE | `common.md` running, verification skills |
| DB writes | Who runs DB write SQL? | The developer. Claude only writes SQL and runs read-only queries | `common.md`, `db.md`, `db-analyst` tools |
| Mandatory checks | Make lint and build checks mandatory for every task and commit? | No, pick them when needed | `common.md` verification |
| Task tracking | Where are tasks and issues tracked, and what does an issue key look like? | Propose the key shape found in the fingerprint's commits and branches (`ABC-123`, `#45`); if none, "none" | `git.md` branch names, commit and PR linking rules |
| Commit authority | How far may Claude go with commit, push and PR? | Commit on request; push, PR and merge only on separate request | `git.md` never section |

## Round 3 — Git details (only what the fingerprint did not settle)

| Item | Question | Default | Affects |
|---|---|---|---|
| Commit format and language | Subject format, language and scope list? | The fingerprint's existing convention (format and language judged separately). If there is no convention, `type(scope): description`, types `feat·fix·refactor·chore·docs·test`, scope = sub-projects + `repo`, language = document language | `git.md` |
| Required trailer | Is there a trailer every commit must carry? | A trailer from the README contributing section, `.github/dco.yml`, or on 2/3+ of the history (`Signed-off-by`, etc.). If none, "none" | `git.md`, `devkit:commit` |
| AI attribution | Add AI attribution such as `Co-Authored-By` to commits and PRs? | Do not add (overrides the system guidance) | `git.md`, `devkit:commit` / `devkit:pr-publish`, team settings.json (`attribution` or `DEVKIT_AI_TRAILER`) |
| Branches, merging, publishing | Branch flow, merge method, and whether to open PR/MRs with the CLI (`gh`/`glab`)? | Propose from the fingerprint's branch list and "Merge targets" (e.g. `feat/*` · `fix/*` → `dev` → PR → `main`, merge commits). PRs merged on the host may not show in local history | `git.md`, `devkit:pr-publish` |

## Environment check (with round 3)

Show the values found in the fingerprint's "Runtime environment" and in README and config files **as a table in the message right before the question**, then ask briefly ("Are the local run values above right?"). Options: `Correct (Recommended)` · `Partly different (tell me the other values)` · `Not checked`. Split local running and DB/deploy into two questions. Never ask for or write credentials (write only how they are delivered).

- `Correct` → write the value and source, with "user confirmed (date)" in the checked scope.
- `Not checked` → write the value and a link to the source file, with "from config files · not verified by running or connecting" in the checked scope.

- Runtime and build tool versions, local addresses and ports, run profiles
- DB and external service access paths (VPN, tunnels, proxies)
- Deploy flow and deploy addresses, whether a production environment exists

## Records

Record answers in the scratchpad `decisions.md` as `Item | Answer | Date`, and write only the resulting sentences in the rules docs. Evidence files read by hand outside the fingerprint (README, config, CI, scripts) also go into the "Evidence files" table of `decisions.md` as `File | Fact taken`.
