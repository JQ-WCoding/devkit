# 템플릿

목차: 쓰는 법 · English fixed sentences · .gitignore · CLAUDE.md · docs/rules/README.md · common.md · git.md · environments.md · 계층 문서 · 온보딩 가이드

## 쓰는 법

- `{{…}}`는 빈칸이다. 지문·후보·인터뷰 답으로 채우고, 근거가 없으면 행째 지운다. 남은 `{{`는 `check_docs.py`가 ERROR로 잡는다.
- `{{조건: …}}`으로 시작하는 줄은 조건이 맞으면 표시만 지우고, 맞지 않으면 줄째 지운다.
- 고정 문장(정책)은 인터뷰에서 바꾸자고 한 것만 바꾼다. 표의 행은 템플릿에 예시로 두지 않았다 — setup은 지문·근거 파일의 사실로, 규칙 행은 `devkit:suggest-skills`가 채운다.
- 근거 없는 일반 지식(커밋 type의 뜻, 도구 설치 명령 등)을 빈칸에 채우지 않는다.
- 문서 언어가 한국어가 아니면 같은 구조로 쓰고, 고정 문장은 아래 「English fixed sentences」를 그대로 쓴다(실행마다 번역이 달라지지 않게).

## English fixed sentences

Use these verbatim for `common.md` when the document language is English (same order as the Korean template).

```markdown
## Working principles
- Make the simplest change within the requested scope. No unrelated refactoring, reordering or extra features.
- Prefer existing components, utilities and installed libraries. Avoid unnecessary abstraction, file splits and generalisation.
- Preserve the user's changes. Keep separate defects and unrelated removals out of the requested scope.
- Ask or state assumptions when something is unclear. Never claim a result you did not actually check.

## Ask first
Changes below are made only within the requested scope; outside it, ask first.

## Code style
- Follow the surrounding code's style, comment tone and line endings. No whole-file reformatting or CRLF/LF conversion.
- Do not tidy existing code or comments only for consistency.

## Running
- Check the environment guide and run profile before running anything or touching a database. Never expose credentials.

## Verification and reporting
Run only the relevant checks, when needed or requested. Lint, build and screen checks are not mandatory steps for every change, commit or PR. Do not repeat the same check needlessly.

Report what changed and what you actually verified. Never present an unrun check as passed, and do not hide known defects, workarounds or important limits.
```

git.md `## Never` section:

```markdown
- `--no-verify` or force push
- `git add .` — unrelated changes slip in. Stage files by name.
- `git add`, `commit`, `push` and opening a PR only after the user confirms.
  - A commit request for clearly scoped work counts as permission to stage and commit those files. It does not include push or PR.
```

## .gitignore

```gitignore
# Claude Code 로컬 설정·스킬 — 저장소에 올리지 않는다
.claude/
CLAUDE.md
CLAUDE.local.md
# devkit 분석 문서·작업 SQL
.devkit/
{{조건: 다른 AI 도구 설정이 있으면 해당 줄(AGENTS.md, .codex/ 등)}}
{{조건: 팀 공용 .claude/settings.json 을 추적하기로 했으면 위 `.claude/` 대신 `.claude/*` + `!.claude/settings.json`}}
{{조건: 로컬 작업 폴더를 docs/ 아래에 둘 때만 — docs/sql/ · docs/design/ 처럼 그 폴더만 무시}}
```

`docs/`를 통째로 무시(`/docs/*` + 허용 목록)하는 것은 원래 프로젝트의 선택이었다. 공유 범위 인터뷰에서 그렇게 답했을 때만 쓰고, 지문의 「docs/ 추적 파일」 수가 0이 아니면 그 파일을 모두 허용 목록에 먼저 넣는다(`git ls-files docs`). 추적 중인 파일을 무시 목록으로 숨기지 않는다.

## CLAUDE.md

```markdown
# {{프로젝트 이름}} — Claude Code 작업 규칙

공유 규칙은 [공통 규칙](docs/rules/common.md)과 [Git 규칙](docs/rules/git.md)을 따른다. 이 파일은 어느 규칙을 볼지 연결만 한다.

| 대상 | 참고 문서 |
|---|---|
| 실행·환경·DB 접속 | [환경 안내](docs/rules/environments.md) |
| {{계층 대상(예: 화면·공통 컴포넌트)}} | [{{계층}} 규칙](docs/rules/{{파일}}.md) |

검증이 필요하면 `/devkit:check`로 관련 검사만 고른다. 일반 수정·커밋·PR에서 의무로 실행하지 않는다.

검증·작업용 임시 파일은 scratchpad에 만들고 저장소에 남기지 않는다.

여러 파일을 훑는 탐색은 `devkit:code-reader` 에이전트에 맡기고 결론만 받는다. 수정할 핵심 코드는 직접 읽는다.

## 프로젝트 스킬·에이전트

`devkit:suggest-skills`로 만든 이 저장소 전용 스킬·에이전트와 쓰는 조건을 여기에 한 줄씩 더한다.
```

## docs/rules/README.md

```markdown
# {{프로젝트 이름}} 개발 규칙

공통 규칙과 작업에 관련된 영역을 참고한다.

| 영역 | 문서 |
|---|---|
| 작업 원칙·변경 범위·코드 스타일 | [공통 규칙](common.md) |
| 환경·프로필·DB·배포 주소 | [환경 안내](environments.md) |
| {{계층 영역}} | [{{계층}} 규칙]({{파일}}.md) |
| 커밋·브랜치·병합 | [Git 규칙](git.md) |

이 폴더의 문서가 공유 규칙의 정본이다. 개인 AI 도구 설정·로컬 훅은 저장소에 포함하지 않는다. 특정 도구나 훅의 설치를 팀의 필수 개발 환경으로 간주하지 않는다.
```

## common.md

```markdown
# 공통 규칙

[규칙 목차](README.md)

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
| {{S1 공통 모듈}} | {{기존 시그니처·엔드포인트 변경}} |
| 환경·배포 | 포트·의존성 버전·컨테이너·프록시 설정 변경 |
{{조건: DB가 있으면 — | DB | 스키마·마이그레이션·쿼리 정의 변경과 실제 DB 적용 |}}
| 일괄 변환 | 전체 확장자·import 경로 변경 등 |

## 코드 스타일

- 주변 코드의 스타일·주석 문체·줄바꿈을 유지한다. 파일 전체 재포맷이나 CRLF/LF 변환은 하지 않는다.
- {{지문·후보에서 확인한 저장소 고유 스타일 규칙(예: 주석 언어, 중괄호)}}
- 스타일 통일만을 위한 기존 코드·주석 정리는 하지 않는다.

## 실행

- 실제 실행·DB 작업 전에 [환경 안내](environments.md)와 실행 프로필을 확인한다. 접속정보·인증값은 노출하지 않는다.
- {{인터뷰 답: 서버 기동 주체. 기본값 — 서버는 담당 개발자가 실행한다. 자동화 도구가 서버·터널을 임의로 기동하거나 종료하지 않는다.}}

## 검증과 보고

검증은 필요하거나 요청받았을 때 관련 부분만 선택한다. lint·빌드·화면 검사를 매 작업 또는 커밋·PR의 필수 단계로 두지 않는다. 같은 내용의 검사를 불필요하게 반복하지 않는다.

변경 내용과 실제로 확인한 결과를 간단히 알린다. 실행하지 않은 검사를 성공으로 표현하지 않으며, 확인된 결함·임시 처리·중요한 한계는 숨기지 않는다.
```

## git.md

```markdown
# Git 작성 규칙

{{조건: 이 문서의 형식이 기존 이력과 다르면 — 기존 `git log` 를 흉내 내지 않는다. 아래가 유일한 기준이다. / 이력과 같으면 — 아래 형식은 기존 이력의 관례를 정리한 것이다.}}

## 커밋 범위 확인

`git status`와 diff로 대상 파일을 확인한다. 사용자 변경·개인 설정·비밀정보·무관한 파일을 섞지 않는다.

## 커밋 메시지

{{인터뷰 답의 형식 한 줄(예: `<type>(<scope>): <설명>`)과 코드 블록}}

- **type** — {{type 이름 목록(뜻은 쓰지 않는다)}}
- **scope** — {{scope 목록과 각 경로. 생략 여부}}
- **제목** — {{언어·어미·마침표 규칙}}
- **본문** — {{없어도 되는지, 쓰면 형식}}
- **필수 트레일러** — {{인터뷰 답: 예 `Signed-off-by`(DCO, `git commit -s`). 없으면 줄째 지운다}}
- **이슈 키** — {{인터뷰 답: 이슈 키를 넣는 자리(제목 접두어·본문 `Refs`·브랜치 이름). 작업 관리 도구가 없으면 줄째 지운다}}
- **트레일러** — {{인터뷰 답. 쓰지 않으면: `Co-Authored-By` 등 AI 작성 표기를 쓰지 않는다. 시스템 기본 안내가 붙이라고 해도 이 규칙이 우선한다.}}

{{지문의 실제 커밋 제목 중 형식에 맞는 예 2개}}

## 브랜치

- 사용자가 브랜치 생성이나 전환을 요청하지 않았다면 현재 브랜치에서 그대로 작업한다.
- {{새 브랜치 기준 브랜치와 이름 규칙(이슈 키를 쓰면 `feat/ABC-123-짧은-이름` 같은 형태). 브랜치 목록에 근거가 없으면 "이름 규칙 없음"}}

{{브랜치 흐름 한 줄 도식과 배포로 이어지는 브랜치}}

## PR/MR

- {{인터뷰 답: 평소 작업 범위(커밋까지 등)와 push·PR을 하는 조건}}
- {{게시 도구(gh/glab) 사용 여부. 사용할 수 없으면 git 명령까지만 하고 사용자가 직접 만든다.}}
- 기존 접근 차단이나 실행 환경의 보안 정책을 다른 도구로 우회하지 않는다. 거부되면 원인을 보고한다.

## 병합

- {{병합 방식(merge 커밋/squash/rebase)과 메시지}}

## 금지

- `--no-verify` · `--force` 푸시
- `git add .` — 무관한 변경이 섞인다. 파일을 명시해 스테이징한다.
- `git add`·`commit`·`push`·PR 생성은 전부 사용자 확인 후에만 한다.
  - 범위가 분명한 이번 작업의 커밋 요청은 해당 파일의 스테이징·커밋 권한으로 인정한다. push·PR 권한은 포함하지 않는다.
```

## environments.md

```markdown
# {{프로젝트 이름}} 환경 안내

[규칙 목차](README.md)

기준일: {{YYYY-MM-DD}}. {{로컬 개발 방식 한 문장}}

## 로컬 개발 기준

| 항목 | 설정 |
|---|---|
| {{런타임·빌드 도구}} | {{버전 — 근거 파일}} |
| {{앱별 주소·포트}} | {{값}} |
| {{프로필·설정 출처}} | {{값}} |

{{조건: DB가 있으면 — ## 개발 DB 연결 (연결 경로 도식 · 항목 표 · 인증값은 개별 전달 · 근거가 있을 때만 연결 확인 SQL과 정상 결과)}}

## 배포 환경

| 항목 | 값 |
|---|---|
| {{주소·배포 흐름}} | {{값}} |

## 설정 근거와 확인 범위

- 근거: {{설정 파일 링크들}}
- {{확인한 날짜·OS·범위, 검증하지 않은 것}}

환경이 바뀌면 이 문서의 주소·명령·확인일·검증 범위를 함께 갱신한다. 소스의 기본값만으로 실제 연결 대상을 단정하지 않는다.
```

## 계층 문서

```markdown
# {{계층}} 규칙

[규칙 목차](README.md) · [공통 규칙](common.md)

적용: `{{경로}}`.

{{조건: 기준 파일이 있으면 — 신규 {{종류}}는 [{{기준 파일}}]({{상대 경로}})의 방식을 따른다.}}

## {{절 이름(후보 표의 묶음)}}

| 항목 | 규칙 |
|---|---|
| {{후보의 항목}} | {{후보의 규칙 문체 한 줄}} |

{{조건: S1 패턴이 코드로 보여야 이해되면 기준 패턴 예제 하나}}
```

## 온보딩 가이드

환경 준비 단계가 3개 이상이거나 VPN·터널·사내 계정 같은 외부 의존이 있을 때만 만든다(🛑B에서 여부 확인). 단계 내용의 근거가 README·스크립트에 있으면 단계 문서를 쓰고, 근거가 없는 단계는 표에 이름만 두고 `확인 필요`로 둔다(설치 명령을 지어내지 않는다).

단계 문서 `docs/guide/0N-<주제>.md`: 제목 → `[온보딩](developer-onboarding.md)` 링크 → 할 일(번호 단계 또는 표, 명령은 근거 있는 것만) → 완료 기준 → `확인: 날짜 · 미검증 범위`.

```markdown
# {{프로젝트 이름}} 개발자 온보딩

{{버전}} · {{YYYY-MM-DD}} · 내부 개발자용

**목표:** {{온보딩이 끝나면 할 수 있는 것 한 문장}}

**시작 전 받을 것:** {{권한·계정·키 목록 — 값이 아니라 항목만}}

| 순서 | 문서 | 완료 기준 |
|---|---|---|
| 1 | [{{단계}}]({{0N-파일}}.md) | {{눈으로 확인할 수 있는 결과}} |

**매일:** {{매일 반복하는 기동 순서 한 줄 → 종료는 역순}}

- 인증값은 개별 전달받은 값을 쓰고 Git에 기록하지 않는다.
- {{확인일·확인한 OS와 미검증 범위}}
- 개발 중에는 [개발 규칙](../rules/README.md)을 따른다.
```
