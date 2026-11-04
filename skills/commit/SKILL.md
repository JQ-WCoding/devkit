---
name: commit
description: 변경을 저장소 커밋 규칙(없으면 기존 관례)에 맞춰 파일을 지정해 스테이징하고 커밋한다. "커밋해줘", "나눠서 커밋해줘"에 쓴다.
argument-hint: "[커밋할 경로...]"
---

# 커밋

## 1. 규칙 고르기

**규칙 출처**(먼저 찾은 것이 기준): `docs/rules/git.md` → `CLAUDE.md`·`CONTRIBUTING.md`·README의 기여(Contributing) 절·`.github/`(PR 템플릿·`dco.yml`) → 최근 이력(`git log --no-merges -30 --format='%s%n%b'`).

아래 세 가지를 **따로** 정한다.

| 항목 | 규칙에 있으면 | 없으면 이력에서 3분의 2 이상 | 그래도 없으면 |
|---|---|---|---|
| 형식 | 그대로 | 그 형식(`type(scope): …`·명령형 문장 등) | `<type>(<scope>): <설명>` — type `feat`·`fix`·`refactor`·`chore`·`docs`·`test`, scope는 바뀐 하위 프로젝트(전역이면 `repo`) |
| 언어 | 그대로 | 그 언어 | 사용자와 대화하는 언어 |
| 필수 트레일러 | 그대로(DCO면 `git commit -s`) | 그 트레일러(`Signed-off-by` 등) | 붙이지 않는다 |

- 제목은 무엇을 했는지만 쓴다. 본문은 필요할 때 짧은 불릿 3줄 이내.
- `-s`로 서명하면 사용자 이름으로 DCO에 동의하는 것이므로, 이 저장소에서 처음 서명할 때 한 번 알린다.

**이슈 키**: 저장소 규칙에 이슈 키(`ABC-123`, `#45` 등)를 넣는 자리가 있으면 그대로 따른다. 규칙이 없으면 넣지 않고, 이번 작업에 이슈 키가 있으면 넣을지 한 번 묻는다.

**AI 작성 표기**(`Co-Authored-By: Claude …`·`Generated with …`): 저장소 규칙이 요구할 때만 붙인다. devkit은 팀이 설치한 사용자 측 규칙이므로, Claude Code 호스트의 기본 작성자 표기 안내보다 이 기준이 우선한다.

## 2. 범위 확인

- `git status --porcelain`과 `git diff`·`git diff --cached`로 대상을 확인한다.
- 이번 요청의 변경만 담는다. 사용자의 다른 작업·개인 설정·비밀값(`.env` 등)·임시 파일은 넣지 않는다.
- 이미 스테이징된 파일이 있으면 이번 커밋에 넣을지 묻는다. 임의로 unstage하지 않는다.
- 한 파일 안에 이번 변경과 무관한 변경이 섞여 있으면 알리고 지시를 받는다(대화형 `git add -p`는 쓸 수 없다).
- 서로 다른 목적(기능 + 무관한 수정, 하위 프로젝트 여러 곳)이 섞였으면 나눠 커밋하자고 제안한다.

## 3. 커밋

```bash
git add -- <파일...>
git commit -F <scratchpad>/commit-msg.txt
git log -1 --stat
git status --porcelain
```

- 메시지는 scratchpad 파일로 넘긴다.
- 일괄 스테이징·훅 우회·`--amend`는 devkit 가드 훅이 막거나 묻는다. pre-commit 훅이 실패하면 원인을 보고한다. 훅이 파일을 고쳤으면 그 변경을 보여 주고 다시 스테이징할지 묻는다.

## 4. 보고

커밋 해시·제목·포함 파일, 남겨 둔 변경을 알린다. push하지 않았다고 밝히고, 요청받으면 `devkit:push`로 한다.
