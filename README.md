# devkit

어느 저장소, 어느 업무 영역에서나 같은 개발 흐름을 까는 Claude Code 팀 개발 키트다. 프로젝트 규칙을 미리 담아 두지 않고, 특정 작업 관리 도구(Jira·Notion·Obsidian·GitHub Issues …)에도 기대지 않는다. 담는 것은 **개발 흐름**(분석 → 구현 → 검증 → 커밋 → push → PR/MR), **일하는 원칙**(범위 최소·확인한 것만 확인했다고 말하기·검증은 선택·사람이 승인하는 지점), 그리고 **그 저장소에 맞는 규칙과 스킬을 근거로 키워 가는 도구**다.

## 들어 있는 것

| 단계 | 이름 | 하는 일 |
|---|---|---|
| 항상 | 세션 훅 `using-devkit` | 세션 시작·재개·압축 때 판단 원칙(6줄)을 넣는다. 저장소의 `CLAUDE.md`·`docs/rules/`가 있으면 그쪽이 우선 |
| 항상 | 가드 훅 `hooks/guard.py` | 셸 명령 실행 직전에 Git·서버 기동 규칙을 코드로 강제한다(아래 「가드 훅」) |
| 분석 | `/devkit:analyze` | 요구·이슈·버그를 어떤 도구에서 왔든 읽고 현행 추적 → 차이 → 영향 범위 → 공통 위험 점검 → 구현 계획을 분석 문서로 만들고 승인받는다 |
| 구현 | `/devkit:develop` | 승인된 계획대로 구현, DB 변경·복구 SQL, 검증과 회귀 확인, 요구 항목별 보고 |
| 검증 | `/devkit:check` | lint·타입·빌드·테스트 명령을 찾아 관련된 것만 실행한다(직접 호출 전용) |
| 커밋 | `/devkit:commit` | 저장소 Git 규칙대로 파일을 지정해 커밋한다 |
| push | `/devkit:push` | 올라갈 커밋·원격 앞섬을 확인하고 보호 브랜치·force push를 막으며 올린다 |
| PR/MR | `/devkit:pr-publish` | 리뷰 → 제목·본문 초안 → 확인 → `gh`/`glab`으로 PR·MR 생성·갱신 |
| 세팅 | `/devkit:setup` | 공유 규칙 골격 `docs/rules/`(공통·Git·환경, 필요하면 계층 문서·온보딩), 로컬 라우터 `CLAUDE.md`, `.gitignore`를 깐다 |
| 세팅 | `/devkit:suggest-skills` | 코드 핀포인트·반복 작업·사용자 교정을 근거로 규칙 행·프로젝트 스킬·에이전트를 제안하고, 고른 것만 만든다 |
| 탐색 | 에이전트 `devkit:code-reader` | 여러 파일을 훑는 탐색을 맡고 결론만 돌려준다(Sonnet, 읽기 전용) |

`analyze`의 공통 위험 점검표는 업무 영역과 관계없이 사고가 반복되는 지점(정합성·동시성·멱등성·상태 전이·금액·시간대·권한 범위·개인정보·외부 연동·대량 처리·배포 호환)을 담는다.

`suggest-skills`가 조건이 맞을 때 제안하는 설계도: 프로젝트 고유 흐름 스킬(`analyze`·`develop` 위에 이 저장소만의 단계를 더함), `db-analyst`·`knowledge-reader`·`spec-analyst` 에이전트, `workspace-cleanup`, `visual-docs`, 외부 도구 스킬.

## 쓰는 흐름

1. 저장소에 처음 쓸 때 `/devkit:setup` → 인터뷰 몇 개에 답하고 구성안을 승인하면 규칙 골격이 생긴다.
2. 작업마다 `/devkit:analyze <이슈 링크·파일·요구>` → 승인 → `/devkit:develop` → 필요하면 `/devkit:check` → `/devkit:commit` → `/devkit:push` → `/devkit:pr-publish`.
3. 가끔 `/devkit:suggest-skills` → 이 저장소만의 규칙 행과 스킬·에이전트 후보를 근거와 함께 받고 고른 것만 만든다. 같은 작업을 반복하거나 같은 교정을 두 번 하면 Claude가 한 번 제안한다.

분석 문서와 작업 SQL은 `<저장소>/.devkit/work/<작업 ID>/`에 둔다(Git 제외).

## 요구 사항

**Python 3.8 이상, `python3` 명령.** 훅·스캔·점검 스크립트가 모두 Python으로 돈다. 다른 실행기(node·bash·PowerShell)는 필요 없다.

| OS | 설치 | 확인 |
|---|---|---|
| macOS | 기본 포함(없으면 `xcode-select --install` 또는 `brew install python`) | `python3 --version` |
| Linux | 배포판 패키지(`apt install python3` 등) | `python3 --version` |
| Windows | python.org의 Python install manager 또는 Microsoft Store의 Python | 새 터미널에서 `python3 --version` |

Windows의 예전 python.org 설치본은 `python3` 명령이 없다. install manager로 다시 설치한다. `python3`를 실행했을 때 Microsoft Store가 열리면 아직 설치되지 않은 것이다.

## 설치

필요: Claude Code, Python 3.8 이상, Git. PR/MR 게시에는 `gh` 또는 `glab`.

로컬 폴더에서:

```bash
claude plugin marketplace add ~/work/devkit
claude plugin install devkit@devkit
```

Git 저장소에 올린 뒤에는 경로 대신 저장소 주소(`claude plugin marketplace add https://<호스트>/<그룹>/devkit.git`)를 쓴다. 세션 안에서는 `/plugin marketplace add …`, `/plugin install devkit@devkit`.

업데이트: `claude plugin marketplace update devkit` 후 `claude plugin update devkit@devkit`, 그리고 Claude Code를 다시 시작한다.

## 팀 저장소에 기본으로 켜기

팀 저장소의 `.claude/settings.json`(Git 추적)에 넣는다. 팀원이 저장소를 신뢰하면 마켓플레이스가 등록되고 플러그인이 켜진다.

```json
{
  "extraKnownMarketplaces": {
    "devkit": { "source": { "source": "git", "url": "https://<호스트>/<그룹>/devkit.git" } }
  },
  "enabledPlugins": { "devkit@devkit": true }
}
```

- GitHub이면 `{ "source": "github", "repo": "<owner>/devkit" }`.
- 팀원마다 처음 한 번은 `claude plugin install devkit@devkit --scope project`로 내려받아야 할 수 있다.
- 이 경우 `.gitignore`는 `.claude/` 전체가 아니라 `.claude/*`와 `!.claude/settings.json`으로 둔다(`devkit:setup`이 인터뷰에서 묻는다).

## 가드 훅

매번 예외 없이 지켜야 하는 규칙은 문장(권고)이 아니라 코드(결정적)로 강제한다. 문장으로는 판단이 필요한 원칙만 남겨 매 세션 토큰을 줄인다. 훅은 셸을 거치지 않고 `python3`로 직접 실행되므로(exec form) macOS·Linux·Windows에서 같게 동작한다.

| 판정 | 명령 (Bash·PowerShell 도구 모두) |
|---|---|
| 막음 | `git add .`·`-A`·`-u`, `git commit -a`·`-n`·`--no-verify`, `git push -f`·`--force`·`+ref`·`--no-verify`, AI 작성 표기(`Co-Authored-By: Claude`·`Generated with Claude Code`)가 든 커밋 메시지(`-m`·heredoc·`-F` 파일) |
| 확인 | `--force-with-lease`, `--amend`, 보호 브랜치(`main`·`master`·`release/*`·`prod*`)로 push, 서버·컨테이너 기동(`bootRun`·`spring-boot:run`·`npm run dev`·`docker compose up` 등) |

- 끄기: `DEVKIT_GUARD=off`. AI 작성 표기를 붙이는 저장소: `DEVKIT_AI_TRAILER=allow`. 둘 다 settings의 `env`에 둘 수 있다.
- 표기가 처음부터 만들어지지 않게 하는 설정(`"attribution": {"commit": "", "pr": ""}`)은 `devkit:setup`이 인터뷰 답에 따라 쓴다.
- 가드 오류는 작업을 막지 않는다(`onFailure: continue`). 애매한 명령은 통과시킨다(오탐보다 미탐).
- 시험: `python3 -I hooks/guard_test.py`

## 원칙을 고치거나 스킬을 더할 때

- 작업 원칙: `skills/using-devkit/SKILL.md`. 매 세션 들어가므로 판단이 필요한 것만 짧게 둔다. 코드로 판정할 수 있는 규칙은 `hooks/guard.py`에 더하고 `guard_test.py`에 사례를 넣는다.
- 새 스킬: `skills/suggest-skills/references/skill-authoring.md`를 따르고 `python3 -I skills/suggest-skills/scripts/check_skill.py skills/<이름>`으로 점검한다.
- 매니페스트 점검: `claude plugin validate .`
- 설치본은 버전별 사본이다. 고친 내용을 팀에 내보내려면 `.claude-plugin/plugin.json`의 `version`을 올린다(같은 버전이면 `plugin update`가 반영하지 않는다).
- 프로젝트마다 다른 내용(모듈 이름·경로·명명)은 devkit에 넣지 않는다. 그건 각 저장소의 `docs/rules/`와 `.claude/`에 둔다.

## 상태

0.3.0 · 2026-11-04. 로컬 시험 단계라 라이선스는 아직 정하지 않았다. 공개하기 전에 `LICENSE`를 더한다.
