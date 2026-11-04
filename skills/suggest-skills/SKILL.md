---
name: suggest-skills
description: 저장소와 작업 이력을 근거로 이 프로젝트에 맞는 규칙 행(docs/rules), 프로젝트 스킬, 읽기 전용 에이전트를 제안하고, 사용자가 고른 것만 만든다. 근거는 코드 핀포인트(필수 경유 모듈·계약·명명·fix 커밋에서 나온 주의·기준 파일), 반복된 다단계 작업, 사용자가 두 번 이상 고쳐 준 내용이다. "이 프로젝트에 필요한 스킬 제안해줘", "규칙에 추가할 거 찾아줘", "이 작업 스킬로 만들어 둘까", "fix 커밋 보고 규칙 갱신해줘" 같은 요청에 사용한다. 저장소에 기본 규칙 골격이 없으면 devkit:setup을 먼저 쓴다.
argument-hint: "[rules | skills | all] [--since YYYY-MM-DD]"
---

# 규칙·스킬·에이전트 제안

**근거 없이는 제안하지 않는다.** 근거는 대상 저장소의 `파일:줄`·커밋·지문 수치, 이 대화에서 반복된 작업, 사용자가 고쳐 준 말이다. 다른 프로젝트에서 본 규칙을 옮기지 않는다.

| 참고 | 언제 |
|---|---|
| [catalog.md](references/catalog.md) | 무엇을 어떤 조건에서 제안하나 |
| [pinpoint-checklist.md](references/pinpoint-checklist.md) | 규칙 행 후보 찾기 — 서브에이전트에도 경로를 준다 |
| [skill-authoring.md](references/skill-authoring.md) | 고른 스킬·에이전트를 만들 때 |
| 설계도: [project-flow](references/blueprints/project-flow.md) · [db-analyst](references/blueprints/db-analyst.md) · [knowledge-reader](references/blueprints/knowledge-reader.md) · [spec-analyst](references/blueprints/spec-analyst.md) · [workspace-cleanup](references/blueprints/workspace-cleanup.md) · [visual-docs](references/blueprints/visual-docs.md) · [tool-skill](references/blueprints/tool-skill.md) | 만들기로 한 것만 읽는다 |

인자: `rules`는 규칙 행만, `skills`는 스킬·에이전트만, 없으면 둘 다.

기준점(`--since`): 인자 → `docs/rules/`의 마지막 커밋 날짜(`git log -1 --format=%ad --date=short -- docs/rules`) → 전체 이력(`docs/rules/`를 방금 만들어 커밋이 없을 때도). 기준점 이후 커밋이 20개 미만이면 그 전 규칙 커밋 날짜로, 그래도 적으면 전체 이력으로 넓힌다. 기준점은 **새 fix 후보를 좁히는 데만** 쓰고, "같은 실수가 반복되는가"는 전체 이력으로 센다.

## 0. 대상 확인

- `docs/rules/`가 없으면 `devkit:setup`을 먼저 하자고 제안한다. 사용자가 그냥 진행하라면 제안만 하고 규칙 행은 보고에 남긴다.
- 이미 있는 프로젝트 스킬·에이전트(`.claude/skills/`·`.claude/agents/` 목록과 각 description), `CLAUDE.md`(「프로젝트 스킬·에이전트」 절이 없으면 전체), 사용자 레벨·다른 플러그인 스킬 목록을 읽어 겹치는 제안을 막는다. `disable-model-invocation` 스킬은 목록에 안 보이므로 폴더를 직접 본다.

## 1. 근거 모으기

**지문**(실행할 스크립트):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/scan_repo.py" <저장소 루트> [--since <기준점>] --out <scratchpad>/fingerprint.json > <scratchpad>/fingerprint.md
```

**규칙 행 후보**(`rules`·전체):

- 계층(하위 프로젝트·DB·인프라)마다 `devkit:code-reader`를 **한 메시지에서 동시에** 띄운다(effort lower). 하위 프로젝트 안이라도 fix 핫스팟이 몰린 하위 앱이나 규칙 문서가 "별도"라고 적은 경로는 따로 띄운다. 작은 저장소(소스 파일 200개 미만이고 계층 2개 이하)는 메인이 직접 한다.
- 브리프에 넣을 것: 맡은 경로, 지문에서 그 경로에 해당하는 줄(내부 모듈·호출·경로 모양·주의 주석·fix 커밋 중 그 경로 것), 해당 `docs/rules/<계층>.md`의 경로와 "직접 읽고 이미 있는 행은 뺀다", [pinpoint-checklist.md](references/pinpoint-checklist.md) 절대 경로(`${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/references/pinpoint-checklist.md`)와 "채택 기준·영역별 질문·후보 형식을 따른다", "후보 표만 돌려준다 — `확인` 행 우선, 15행까지", "맡은 경로의 fix 커밋만 읽는다".
- 지문 「확장자 상위」에 일반 소스가 아닌 확장자(리포트 양식·스키마·템플릿)가 있으면 그 부속 기능을 브리프에 따로 적는다. 빠뜨리면 그 절이 통째로 빠진다.
- 서브에이전트가 `확인`으로 올린 S1·S3 행도 문서에 쓰기 전에 메인이 근거 파일이나 `git show`를 직접 본다(커밋 성격을 잘못 읽는 일이 있다).
- 여러 계층에 걸친 fix 커밋은 메인이 `git show`로 읽어 "같은 실수가 다른 파일에서 다시 날 수 있는가"를 판단한다. 보관본·예전 템플릿 폴더(`archive`·`old`·`deprecated` 등)의 fix는 근거로 쓰지 않는다.

**스킬·에이전트 후보**(`skills`·전체): [catalog.md](references/catalog.md)의 조건을 지문·이력과 대조한다. 들어맞는지 판단하려고 설계도를 읽는 것은 괜찮다. 반복 작업은 같은 유형 커밋 묶음(같은 scope·같은 동사, 같은 폴더 패턴), 이 대화에서 같은 단계를 되풀이한 흔적, 사용자가 말해 준 반복 작업에서 찾는다.

**교정**: 이 대화에서 사용자가 같은 지적을 두 번 이상 했으면 규칙 행이나 스킬 내용 후보로 올린다.

서브에이전트가 돌려준 원본 표는 `<scratchpad>/candidates.md`에, 메인이 합치고 판정한 결과는 `<scratchpad>/suggestions.md`(채택 후보·`확인 필요`·버림과 이유)에 저장한다.

## 🛑 제안

한 표로 보여 주고 고르게 한다(AskUserQuestion multiSelect, 한 질문에 4개까지).

| 종류 | 이름·대상 | 왜(근거 한 구) | 만들 것 | 권장 |
|---|---|---|---|---|

- 권장은 3개 이내, 나머지는 "다음 후보"로 한 줄씩.
- 규칙 행은 들어갈 문서별 개수와 대표 행 2~3개를 보여 준다(전체는 `suggestions.md`).
- 없는 계층 문서를 새로 만들어야 하는 규칙 행이 있으면 "새 문서 / 기존 문서의 절"을 따로 단일 선택으로 묻는다.
- 기존 규칙과 코드가 어긋난 곳을 찾았으면 코드 기준으로 차이만 보고한다. 규칙을 몰래 고치지 않는다.

## 2. 만들기 (고른 것만)

- **규칙 행**: 해당 `docs/rules/<계층>.md`에 기존 문체로 더한다. 계층 문서가 없으면 setup의 계층 문서 골격으로 만들고 `docs/rules/README.md` 목차와 `CLAUDE.md` 표에 한 줄씩 더한다.
- **에이전트**: 설계도의 골격을 `.claude/agents/<이름>.md`로 쓴다. `{{…}}`는 근거로 채우고, 근거가 없는 줄은 지운다. DB MCP 도구 이름은 이 세션에서 실제 보이는 이름을 넣는다.
- **스킬**: [skill-authoring.md](references/skill-authoring.md)대로 `.claude/skills/<이름>/`에 만든다 — 평가 시나리오 3개 이상, 규칙은 `docs/rules/` 링크, 스크립트는 `python3 -I`.
- 스킬·에이전트를 만들었으면 `CLAUDE.md`의 「프로젝트 스킬·에이전트」 절에 만든 것과 쓰는 조건을 한 줄씩 더한다.
- 기존 파일은 Edit으로 더하기만 하고 줄바꿈을 보존한다. 커밋하지 않는다.

## 3. 점검

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/check_docs.py" <저장소 루트>
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/suggest-skills/scripts/check_skill.py" <저장소 루트>/.claude/skills/<만든 스킬>
```

`check_skill.py`는 스킬을 만들었을 때만 실행한다. `ERROR`는 고치고 다시 실행한다. 평가 시나리오는 이 세션에서 판정하지 않고, 새 세션에서 대표 요청으로 확인하도록 안내한다.

## 4. 보고

만든 것과 파일, 고르지 않은 후보(다음에 다시 볼 것), 점검 결과, 확인하지 못한 것, 다음 기준점(오늘 날짜·마지막 커밋 해시)을 알린다.
