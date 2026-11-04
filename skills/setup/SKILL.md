---
name: setup
description: 지문 수집과 짧은 인터뷰로 팀 공유 규칙 골격(docs/rules)·로컬 CLAUDE.md·.gitignore를 만들거나 보강한다. "devkit 세팅해줘", "개발 규칙 틀 만들어줘", "CLAUDE.md 깔아줘"에 쓴다.
argument-hint: "[저장소 경로]"
---

# devkit 기본 세팅

방법은 [method.md](references/method.md)를 따른다: 공유 정본 `docs/rules/` + 로컬 라우터 `CLAUDE.md`, 표 중심 짧은 문체, 어느 프로젝트에나 넣는 정책. 규칙 표의 행은 지문·사용자 답에서만 채우고, 근거가 없으면 쓰지 않는다.

| 참고 | 언제 |
|---|---|
| [method.md](references/method.md) | 시작할 때 |
| [interview.md](references/interview.md) | 🛑A |
| [templates.md](references/templates.md) | 2단계 |

스크립트는 실행한다(읽을 필요 없음). 결과는 scratchpad에 둔다.

## 0. 대상 확인

- 저장소 루트(인자 또는 현재 디렉터리), 현재 브랜치, 작업 트리 상태를 확인한다. git 저장소가 아니면 이력 없이 진행할지 묻는다.
- `CLAUDE.md`·`docs/rules/`가 이미 있으면 **보강**이다. 기존 문서를 정본으로 두고 빠진 파일·절만 더한다. 덮어쓰지 않는다.
- `README.md`·`CONTRIBUTING.md`·`AGENTS.md`·`.cursorrules`·`.github/copilot-instructions.md`·설치 문서가 있으면 근거로 읽는다(README에 실행 방법·포트·접속 경로가 있는 경우가 많다). 지우거나 옮기지 않는다.

## 1. 지문 수집

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/scan_repo.py" <저장소 루트> --out <scratchpad>/fingerprint.json > <scratchpad>/fingerprint.md
```

`fingerprint.md`에서 이 단계에 쓰는 것만 본다: 구성(하위 프로젝트), 실행 환경(버전·프로필·포트·프록시), CI, DB 종류, 기존 규칙·AI 설정, `.gitignore`·`docs/` 추적 파일 수, 코드 스타일, Git(원격 호스트·브랜치·합쳐진 대상·커밋 관례·트레일러). 지문에 없는 환경 사실은 설정 파일·CI·스크립트를 직접 읽고, 읽은 파일을 `decisions.md`의 「근거 파일」에 남긴다.

「평문 비밀값 의심」이 나오면 위치만 보고에 적는다. 값을 출력하거나 문서에 옮기지 않는다.

## 🛑 A. 인터뷰

[interview.md](references/interview.md)의 항목 중 지문으로 정해지지 않은 것만 AskUserQuestion으로 묻는다(한 번에 4문항, 2~3번). 환경 값은 지문에서 찾은 것을 보여 주고 맞는지만 묻는다. 답은 `<scratchpad>/decisions.md`에 적는다.

## 🛑 B. 구성안 승인

한 번에 보여 주고 승인받는다. 승인 전에는 저장소에 파일을 만들지 않는다.

- 만들 파일과 한 줄 설명. 계층 문서는 사실 행(적용 경로·언어·런타임·별칭·기준 파일)만 담고, 규칙 행은 `devkit:suggest-skills`에서 더한다고 밝힌다
- 온보딩 가이드(`docs/guide/`)를 만들지와 단계 목록
- `.gitignore`에 더할 줄(이미 다 있으면 "변경 없음"과 이유)과 지문의 `docs/` 추적 파일 수. 만들 파일 경로마다 `git check-ignore -v <경로>`로 무시되는지 확인한다 — 공유할 파일이 무시되면 허용 목록에 더하거나 이름을 기존 허용 이름에 맞춘다
- 저장소 전체 파일을 검사하는 도구(nohttp·라이선스 헤더·markdownlint·맞춤법 검사 등 — CI·빌드 설정에서 찾는다)가 새 문서에도 적용되는지, 그렇다면 그 규칙을 지켜 쓰겠다는 것
- 설정 파일: [templates.md](references/templates.md)의 「.claude/settings.json」 — AI 작성 표기 답에 따라 `attribution` 또는 `DEVKIT_AI_TRAILER`. 팀 devkit 답이 예면 `.claude/settings.json`(자동 설치 키 포함), 아니오면 `.claude/settings.local.json`
- 보강이면 기존 파일별로 더할 내용

## 2. 작성

순서: `docs/rules/`(README → common → git → environments → 계층 문서) → `docs/guide/`(만들 때) → `CLAUDE.md` → `.gitignore` → `.claude/settings.json` 또는 `.claude/settings.local.json`.

- 골격은 [templates.md](references/templates.md)를 쓴다. `{{…}}` 빈칸은 지문·답으로 채우고, 근거가 없으면 행째 지운다.
- 환경 값은 출처(설정 파일 링크)와 함께 쓰고 `기준일`·`확인 범위`를 붙인다. 사용자가 확인한 값은 "사용자 확인", 아니면 "설정 파일 기준 · 실제 실행·접속 미확인". 근거가 아예 없는 값은 `미확인`. 인증값은 전달 방식만 쓴다.
- 기존 파일은 Edit으로 더하기만 하고 줄바꿈(CRLF/LF)을 보존한다.
- 커밋하지 않는다. 요청받으면 `devkit:commit`으로 한다.

## 3. 점검

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/check_docs.py" <저장소 루트>
```

검사 대상은 `CLAUDE.md`·`docs/rules`·`docs/guide`·`.claude/agents`·`.claude/skills`다. ERROR: 깨진 링크·비밀값 형태·채우지 않은 `{{…}}`·에이전트 frontmatter. WARN: 저장소에서 근거를 못 찾은 코드 표기 식별자, 루트 README에서 `docs/rules`·`docs/guide`로 가는 깨진 링크, 길이.

- `ERROR`는 고치고 다시 실행한다.
- 근거 없는 식별자 WARN은 다른 프로젝트에서 옮겼거나 오타인지 확인해 고친다. 의도한 외부 이름(쓰는 도구·표준)이면 `--allow <식별자>`로 다시 실행하고 사유를 보고한다.
- 직접 확인: `CLAUDE.md`가 규칙을 복제하지 않고 링크만 하는가, 일반 지식 행이 섞이지 않았는가, 모든 행의 근거를 `fingerprint.md`·`decisions.md`에서 찾을 수 있는가.

## 4. 보고

만든·고친 파일, 인터뷰 결정, 점검 결과와 남긴 WARN, `.gitignore` 변경, 미확인 환경 값을 알린다. 이어서 할 일로 `devkit:suggest-skills`(이 저장소의 핀포인트 규칙·스킬·에이전트 제안)를 한 줄로 제안한다.
