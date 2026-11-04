# devkit

어느 저장소, 어느 업무 영역에서나 같은 개발 흐름을 까는 Claude Code 팀 개발 키트다. 프로젝트 규칙을 미리 담아 두지 않고, 특정 작업 관리 도구(Jira·Notion·Obsidian·GitHub Issues …)에도 기대지 않는다. 담는 것은 **개발 흐름**(분석 → 구현 → 검증 → 커밋 → push → PR/MR), **일하는 원칙**(범위 최소·확인한 것만 확인했다고 말하기·검증은 선택·사람이 승인하는 지점), 그리고 **그 저장소에 맞는 규칙과 스킬을 근거로 키워 가는 도구**다.

## 들어 있는 것

| 단계 | 이름 | 하는 일 |
|---|---|---|
| 항상 | 세션 훅 `using-devkit` | 세션 시작·재개·압축 때 작업 원칙과 스킬 안내를 넣는다. 저장소의 `CLAUDE.md`·`docs/rules/`가 있으면 그쪽이 우선 |
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

## 원칙을 고치거나 스킬을 더할 때

- 작업 원칙: `skills/using-devkit/SKILL.md`. 매 세션 들어가므로 짧게 유지한다.
- 새 스킬: `skills/suggest-skills/references/skill-authoring.md`를 따르고 `python3 -I skills/suggest-skills/scripts/check_skill.py skills/<이름>`으로 점검한다.
- 매니페스트 점검: `claude plugin validate .`
- 설치본은 버전별 사본이다. 고친 내용을 팀에 내보내려면 `.claude-plugin/plugin.json`의 `version`을 올린다(같은 버전이면 `plugin update`가 반영하지 않는다).
- 프로젝트마다 다른 내용(모듈 이름·경로·명명)은 devkit에 넣지 않는다. 그건 각 저장소의 `docs/rules/`와 `.claude/`에 둔다.

## 상태

0.2.0 · 2026-11-04. 로컬 시험 단계라 라이선스는 아직 정하지 않았다. 공개하기 전에 `LICENSE`를 더한다.
