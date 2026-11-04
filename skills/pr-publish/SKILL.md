---
name: pr-publish
description: 브랜치 변경을 리뷰해 PR/MR 제목·본문 초안을 만들고 확인 후 gh·glab으로 생성·갱신한다. "PR 올려줘", "MR 만들어줘", "MR 본문 갱신해줘"에 쓴다.
argument-hint: "[source 브랜치] [target 브랜치]"
---

# PR/MR 리뷰·게시

코드 수정·commit·push·merge는 이 스킬 호출만으로 승인되지 않는다. 저장소 `docs/rules/git.md`의 브랜치·PR 규칙이 있으면 그것을 따른다.

## 1. 대상 고정

- source는 인자 또는 현재 브랜치, target은 인자 → `git.md`의 흐름 → 원격 기본 브랜치(`git symbolic-ref refs/remotes/origin/HEAD`) 순으로 정한다.
- 원격을 조회하고 SHA를 고정한다. 임의 stash·checkout·reset으로 작업 트리를 바꾸지 않는다.

```bash
git fetch --no-tags origin <source> <target>
git rev-parse origin/<source> origin/<target>
git merge-base origin/<target> origin/<source>
```

- PR에 들어가는 것은 **원격** source다. 로컬에 push되지 않은 커밋이 있으면 포함되지 않는다고 알리고, 요청받으면 `devkit:push`로 올린다.
- 원격 호스트로 도구를 고른다: `git remote get-url origin`의 호스트가 `github.com` 또는 `gh auth status`의 호스트면 `gh`, `gitlab` 도메인 또는 `glab auth status`의 호스트(사내 GitLab 포함)면 `glab`. 어느 쪽도 아니면(파일 경로 원격, 인증 안 됨) **초안 모드**다.

## 2. 리뷰

- 고정한 SHA의 전체 변경 목록과 diff를 읽고, 필요한 호출부는 그 SHA 기준으로 읽는다(`git show <sha>:<경로>`). 로컬 작업 파일이 다르면 PR 코드로 보지 않는다.
- 실제 장애·데이터 오류·회귀, API·스키마 계약, 권한, 트랜잭션, 비밀값 포함 여부를 중심으로 본다. 취향이나 수치만으로 리팩터링을 요구하지 않는다.
- 변경이 크면 파일 묶음별로 `devkit:code-reader`에 호출부 추적을 맡긴다.
- 검사가 필요하면 `devkit:check`를 제안한다(직접 호출 스킬이다).

## 3. 초안과 🛑 확인

- 리뷰 결과(결함은 파일·발생 조건·영향)와 제목·본문 초안을 보여 준다. 제목·본문의 언어와 형식은 `git.md`·PR 템플릿(`.github/pull_request_template.md`·`.gitlab/merge_request_templates/`)을 따르고, 없으면 `devkit:commit`의 형식·언어 판정을 그대로 쓴다.
- 이슈 키가 있으면 `git.md`의 연결 방식(제목 접두어·본문 `Closes #45`·`Refs ABC-123` 등)을 따르고, 규칙이 없으면 본문에 출처 링크만 둔다. 트래커의 상태를 바꾸지 않는다.
- 분석 문서(`.devkit/work/*/analysis.md` 중 브랜치 이름·이슈 키가 맞는 것, 없으면 가장 최근 것을 확인받아)가 있으면 요구 항목·영향 범위·검증 결과·DB 적용 절차를 본문에 요약한다. 분석 문서와 작업 SQL은 저장소에 커밋되지 않으므로, 리뷰어가 알아야 할 SQL 절차는 본문에 쓰고 "이 PR에 포함되지 않음"을 밝힌다.
- 본문에 실행하지 않은 검사를 통과로 쓰지 않는다. AI 작성 표기는 `git.md`의 트레일러 규칙을 따르고, 규칙이 없으면 넣지 않는다.
- 열린 PR/MR이 있는지 확인해 새로 만들지 갱신할지 함께 알린다.
- 초안 모드면 열린 PR 확인과 게시 확인을 건너뛰고, 제목·본문을 scratchpad 파일과 응답으로 전달한 뒤 호스트에서 직접 만들도록 안내하고 끝낸다.
- "이대로 올릴지" 한 번 묻는다. 사용자가 처음부터 "리뷰 후 바로 올려"라고 했고 확인된 결함이 없으면 생략한다. 결함이 있으면 반드시 다시 묻는다.

## 4. 게시

- 게시 직전 원격 SHA를 다시 조회한다. 리뷰한 SHA와 다르면 게시하지 않고 추가된 커밋을 알린다.
- 인증을 확인한다(`gh auth status` / `glab auth status`). 실패하면 게시하지 않고 초안을 전달해 사용자가 직접 만들게 한다. 브라우저 자동화 등 다른 경로로 대신 게시하지 않는다.
- 본문은 scratchpad 파일로 넘긴다.

| 동작 | GitHub (`gh`) | GitLab (`glab`) |
|---|---|---|
| 열린 것 확인 | `gh pr list --head <source> --base <target> --json number,url` | `glab mr list --source-branch <source> --target-branch <target> -F json` |
| 생성 | `gh pr create --head <source> --base <target> --title "<제목>" --body-file <파일>` | `glab mr create --source-branch <source> --target-branch <target> --title "<제목>" --description-file <파일> --remove-source-branch=false --push=false --yes` |
| 갱신 | `gh pr edit <번호> --title "<제목>" --body-file <파일>` | `glab mr update <iid> --title "<제목>" --description-file <파일>` |
| 게시 후 확인 | `gh pr view <번호> --json headRefOid,baseRefName,headRefName,url` | `glab mr view <iid> -F json` |

- `glab mr update`의 `--remove-source-branch`·`--squash-before-merge`는 토글이라 갱신에서 쓰지 않는다.
- 게시 후 source·target·head SHA가 리뷰한 값과 같은지 확인하고 링크를 보고한다.
- merge·auto-merge·승인·리뷰어/담당자 지정은 요청받았을 때만 한다. 병합이 배포로 이어지는 브랜치면 그 점을 알린다.
- 인증 계정이 개인 계정이 아니면(봇 토큰 등) 작성자가 그 계정으로 표시된다고 알린다.
