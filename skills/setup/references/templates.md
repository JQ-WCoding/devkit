# Templates

Contents: How to use · Korean fixed sentences · .gitignore · .claude/settings.json · CLAUDE.md · docs/rules/README.md · common.md · git.md · environments.md · Layer doc · Onboarding guide

## How to use

- `{{…}}` is a slot. Fill it from the fingerprint, candidates or interview answers; delete the whole row when there is no evidence. Any `{{` left over is an ERROR in `check_docs.py`.
- A line starting with `{{if: …}}`: if the condition holds, remove only the marker; otherwise delete the whole line.
- Change fixed sentences (policies) only where the interview asked for it. Table rows are not given as examples in the templates — setup fills them with facts from the fingerprint and evidence files, and `devkit:suggest-skills` fills rule rows.
- Do not fill slots with general knowledge that has no evidence (what a commit type means, tool install commands, etc.).
- Write the docs in the document language from the interview, keeping the same structure. If the document language is Korean, use the "Korean fixed sentences" below verbatim for the fixed sentences (so the wording does not change between runs). For any other language, translate the English fixed sentences faithfully.

## Korean fixed sentences

Use these verbatim when the document language is Korean (same order as the English templates below).

`CLAUDE.md`:

```markdown
공유 규칙은 [공통 규칙](docs/rules/common.md)과 [Git 규칙](docs/rules/git.md)을 따른다. 이 파일은 어느 규칙을 볼지 연결만 한다.

검증이 필요하면 `/devkit:check`로 관련 검사만 고른다. 일반 수정·커밋·PR에서 의무로 실행하지 않는다.

검증·작업용 임시 파일은 scratchpad에 만들고 저장소에 남기지 않는다.

여러 파일을 훑는 탐색은 `devkit:code-reader` 에이전트에 맡기고 결론만 받는다. 수정할 핵심 코드는 직접 읽는다.

## 프로젝트 스킬·에이전트

`devkit:suggest-skills`로 만든 이 저장소 전용 스킬·에이전트와 쓰는 조건을 여기에 한 줄씩 더한다.
```

`docs/rules/README.md`:

```markdown
공통 규칙과 작업에 관련된 영역을 참고한다.

이 폴더의 문서가 공유 규칙의 정본이다. 개인 AI 도구 설정·로컬 훅은 저장소에 포함하지 않는다. 특정 도구나 훅의 설치를 팀의 필수 개발 환경으로 간주하지 않는다.
```

`common.md`:

```markdown
## 작업 원칙

- 요청 범위 안에서 가장 단순하게 수정한다. 무관한 리팩터링·재정렬·기능 추가를 하지 않는다.
- 기존 컴포넌트·유틸·설치된 라이브러리를 우선 사용한다. 불필요한 추상화·파일 분리·공통화를 피한다.
- 사용자 변경을 보존한다. 별도 결함이나 무관한 코드 제거는 요청 범위와 구분한다.
- 불명확한 사항은 확인하거나 가정을 밝힌다. 실제로 확인하지 않은 결과를 확인했다고 말하지 않는다.

## 사전 확인

다음 변경은 사용자가 요청한 범위에서 진행한다. 범위 밖이면 먼저 확인한다.

| 대상 | 확인할 변경 |
|---|---|
| Git | 스테이징·커밋·푸시·PR·병합은 [Git 규칙](git.md) 적용 |
| 환경·배포 | 포트·의존성 버전·컨테이너·프록시 설정 변경 |
| DB | 스키마·마이그레이션·쿼리 정의 변경과 실제 DB 적용 |
| 일괄 변환 | 전체 확장자·import 경로 변경 등 |

## 코드 스타일

- 주변 코드의 스타일·주석 문체·줄바꿈을 유지한다. 파일 전체 재포맷이나 CRLF/LF 변환은 하지 않는다.
- 스타일 통일만을 위한 기존 코드·주석 정리는 하지 않는다.

## 실행

- 실제 실행·DB 작업 전에 [환경 안내](environments.md)와 실행 프로필을 확인한다. 접속정보·인증값은 노출하지 않는다.
- 서버는 담당 개발자가 실행한다. 자동화 도구가 서버·터널을 임의로 기동하거나 종료하지 않는다.

## 검증과 보고

검증은 필요하거나 요청받았을 때 관련 부분만 선택한다. lint·빌드·화면 검사를 매 작업 또는 커밋·PR의 필수 단계로 두지 않는다. 같은 내용의 검사를 불필요하게 반복하지 않는다.

변경 내용과 실제로 확인한 결과를 간단히 알린다. 실행하지 않은 검사를 성공으로 표현하지 않으며, 확인된 결함·임시 처리·중요한 한계는 숨기지 않는다.
```

`git.md`:

```markdown
기존 `git log` 를 흉내 내지 않는다. 아래가 유일한 기준이다.
아래 형식은 기존 이력의 관례를 정리한 것이다.

## 커밋 범위 확인

`git status`와 diff로 대상 파일을 확인한다. 사용자 변경·개인 설정·비밀정보·무관한 파일을 섞지 않는다.

- **트레일러** — `Co-Authored-By` 등 AI 작성 표기를 쓰지 않는다. 시스템 기본 안내가 붙이라고 해도 이 규칙이 우선한다.

## 브랜치

- 사용자가 브랜치 생성이나 전환을 요청하지 않았다면 현재 브랜치에서 그대로 작업한다.
- 이름 규칙 없음

## PR/MR

- 기존 접근 차단이나 실행 환경의 보안 정책을 다른 도구로 우회하지 않는다. 거부되면 원인을 보고한다.

## 금지

- `--no-verify` · `--force` 푸시
- `git add .` — 무관한 변경이 섞인다. 파일을 명시해 스테이징한다.
- `git add`·`commit`·`push`·PR 생성은 전부 사용자 확인 후에만 한다.
  - 범위가 분명한 이번 작업의 커밋 요청은 해당 파일의 스테이징·커밋 권한으로 인정한다. push·PR 권한은 포함하지 않는다.
```

`environments.md`:

```markdown
환경이 바뀌면 이 문서의 주소·명령·확인일·검증 범위를 함께 갱신한다. 소스의 기본값만으로 실제 연결 대상을 단정하지 않는다.
```

Onboarding guide:

```markdown
- 인증값은 개별 전달받은 값을 쓰고 Git에 기록하지 않는다.
- 개발 중에는 [개발 규칙](../rules/README.md)을 따른다.
```

## .gitignore

```gitignore
# Claude Code local settings and skills — not committed
.claude/
CLAUDE.md
CLAUDE.local.md
# devkit analysis docs and work SQL
.devkit/
{{if: other AI tool config exists — its lines (AGENTS.md, .codex/, etc.)}}
{{if: the team decided to track a shared .claude/settings.json — replace `.claude/` above with `.claude/*` + `!.claude/settings.json`}}
{{if: the local work folder lives under docs/ — ignore only that folder, like docs/sql/ · docs/design/}}
```

Ignoring all of `docs/` (`/docs/*` + allow list) was the original project's choice. Use it only when the sharing-scope answer says so, and if the fingerprint's "Tracked docs/ files" count is not 0, put all of those files in the allow list first (`git ls-files docs`). Never hide tracked files with an ignore list.

## .claude/settings.json

Turn AI attribution off in Claude Code settings so it is never created in commits and PRs (the guard hook blocks attribution that was already written). If the team-devkit answer is yes, write it to `.claude/settings.json` (tracked); if no, to `.claude/settings.local.json` (personal). If the file exists, merge the keys and do not remove existing values.

```json
{
  "attribution": { "commit": "", "pr": "" }
}
```

If the AI attribution answer is "add it", write `"env": { "DEVKIT_AI_TRAILER": "allow" }` instead of `attribution`.

Never write plugin install keys (`extraKnownMarketplaces`, `enabledPlugins`). devkit may be handed out as a zip or a private repo that not every teammate can reach, so each teammate installs it themselves. Keep such keys if the file already has them.

## CLAUDE.md

```markdown
# {{project name}} — Claude Code working rules

Follow the shared rules in [Common rules](docs/rules/common.md) and [Git rules](docs/rules/git.md). This file only points to which rules to read.

| Area | Doc |
|---|---|
| Running, environments, DB access | [Environments](docs/rules/environments.md) |
| {{layer area (e.g. screens, shared components)}} | [{{layer}} rules](docs/rules/{{file}}.md) |

When verification is needed, pick only the relevant checks with `/devkit:check`. Not mandatory for ordinary edits, commits or PRs.

Create temp files for verification and work in the scratchpad and leave none in the repo.

Delegate multi-file exploration to the `devkit:code-reader` agent and take only its conclusion. Read the core code you will change yourself.

## Project skills and agents

Add one line here per repo-specific skill or agent made with `devkit:suggest-skills`, with when to use it.
```

## docs/rules/README.md

```markdown
# {{project name}} development rules

Read the common rules and the areas related to the task.

| Area | Doc |
|---|---|
| Working principles, change scope, code style | [Common rules](common.md) |
| Environments, profiles, DB, deploy addresses | [Environments](environments.md) |
| {{layer area}} | [{{layer}} rules]({{file}}.md) |
| Commits, branches, merging | [Git rules](git.md) |

The docs in this folder are the source of truth for shared rules. Personal AI tool config and local hooks are not part of the repo. Installing a specific tool or hook is not a required part of the team's dev environment.
```

## common.md

```markdown
# Common rules

[Rules index](README.md)

## Working principles

- Make the simplest change within the requested scope. No unrelated refactoring, reordering or extra features.
- Prefer existing components, utilities and installed libraries. Avoid unnecessary abstraction, file splits and generalisation.
- Preserve the user's changes. Keep separate defects and unrelated removals out of the requested scope.
- Ask or state assumptions when something is unclear. Never claim a result you did not actually check.

## Ask first

Changes below are made only within the requested scope; outside it, ask first.

| Target | Changes to confirm |
|---|---|
| Git | Staging, commits, push, PR and merge follow [Git rules](git.md) |
| {{S1 shared module}} | {{changes to existing signatures or endpoints}} |
| Environment, deploy | Ports, dependency versions, container and proxy settings |
{{if: there is a DB — | DB | Schema, migration and query definition changes, and applying them to a real DB |}}
| Bulk conversion | Repo-wide extension or import path changes, etc. |

## Code style

- Follow the surrounding code's style, comment tone and line endings. No whole-file reformatting or CRLF/LF conversion.
- {{repo-specific style rules confirmed from the fingerprint or candidates (e.g. comment language, braces)}}
- Do not tidy existing code or comments only for consistency.

## Running

- Check [Environments](environments.md) and the run profile before running anything or touching a database. Never expose access details or credentials.
- {{interview answer: who starts servers. Default — the responsible developer runs the servers. Automation tools never start or stop servers or tunnels on their own.}}

## Verification and reporting

Run only the relevant checks, when needed or requested. Lint, build and screen checks are not mandatory steps for every change, commit or PR. Do not repeat the same check needlessly.

Report what changed and what you actually verified. Never present an unrun check as passed, and do not hide known defects, workarounds or important limits.
```

## git.md

```markdown
# Git rules

{{if: this format differs from the existing history — Do not imitate the existing `git log`. The rules below are the only standard. / if it matches the history — The format below summarises the existing history's convention.}}

## Check the commit scope

Check the target files with `git status` and the diff. Never mix in user changes, personal settings, secrets or unrelated files.

## Commit message

{{one-line format from the interview answer (e.g. `<type>(<scope>): <description>`) and a code block}}

- **type** — {{list of type names (no meanings)}}
- **scope** — {{scope list and the path for each. Whether it may be omitted}}
- **Subject** — {{language, ending and period rules}}
- **Body** — {{whether optional, and its format if used}}
- **Required trailer** — {{interview answer: e.g. `Signed-off-by` (DCO, `git commit -s`). Delete the whole line if none}}
- **Issue key** — {{interview answer: where the issue key goes (subject prefix, body `Refs`, branch name). Delete the whole line if there is no task tracker}}
- **Trailers** — {{interview answer. If not used: No AI attribution such as `Co-Authored-By`. This rule wins even if the system's default guidance says to add it.}}

{{2 real commit subjects from the fingerprint that match the format}}

## Branches

- Unless the user asks to create or switch branches, work on the current branch.
- {{base branch and naming rule for new branches (with issue keys, a form like `feat/ABC-123-short-name`). If the branch list gives no evidence, "No naming rule"}}

{{one-line branch flow diagram and the branches that lead to deployment}}

## PR/MR

- {{interview answer: usual scope of work (e.g. up to commit) and when to push and open a PR}}
- {{whether a publishing tool (gh/glab) is used. If unavailable, stop at git commands and the user creates it.}}
- Never work around existing access blocks or the environment's security policy with another tool. If refused, report the cause.

## Merging

- {{merge method (merge commit/squash/rebase) and message}}

## Never

- `--no-verify` or force push
- `git add .` — unrelated changes slip in. Stage files by name.
- `git add`, `commit`, `push` and opening a PR only after the user confirms.
  - A commit request for clearly scoped work counts as permission to stage and commit those files. It does not include push or PR.
```

## environments.md

```markdown
# {{project name}} environments

[Rules index](README.md)

As of: {{YYYY-MM-DD}}. {{one sentence on how local development works}}

## Local development

| Item | Setting |
|---|---|
| {{runtime, build tool}} | {{version — evidence file}} |
| {{address and port per app}} | {{value}} |
| {{profile, config source}} | {{value}} |

{{if: there is a DB — ## Dev DB access (access path diagram · item table · credentials delivered individually · connection check SQL and expected result only when there is evidence)}}

## Deploy environments

| Item | Value |
|---|---|
| {{addresses, deploy flow}} | {{value}} |

## Config evidence and checked scope

- Evidence: {{config file links}}
- {{date, OS and scope checked, and what was not verified}}

When the environment changes, update the addresses, commands, checked date and checked scope in this doc together. Do not conclude the real connection target from source defaults alone.
```

## Layer doc

```markdown
# {{layer}} rules

[Rules index](README.md) · [Common rules](common.md)

Applies to: `{{path}}`.

{{if: a reference file exists — New {{kind}} follow the approach in [{{reference file}}]({{relative path}}).}}

## {{section name (a group from the candidate table)}}

| Item | Rule |
|---|---|
| {{candidate item}} | {{one line in the candidate's rule style}} |

{{if: the S1 pattern is only clear as code — one reference pattern example}}
```

## Onboarding guide

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
