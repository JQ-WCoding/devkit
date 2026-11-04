---
name: push
description: 올라갈 커밋·대상을 확인하고 원격이 앞서면 합칠 방법을 물은 뒤 push한다. "push해줘", "원격에 올려줘"에 쓴다.
argument-hint: "[원격] [브랜치]"
---

# push

`docs/rules/git.md`의 브랜치·병합 규칙이 있으면 그것이 우선이다.

## 1. 대상 확인

```bash
git status --porcelain
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # upstream 없으면 실패
git ls-remote --heads <원격> <브랜치>                   # 비어 있으면 새 브랜치
```

| 경우 | 올라갈 커밋 | 원격에만 있는 커밋 |
|---|---|---|
| 원격에 브랜치가 있다 | `git fetch --no-tags <원격> <브랜치>` 후 `git log --oneline <원격>/<브랜치>..HEAD` | `git log --oneline HEAD..<원격>/<브랜치>` |
| 새 브랜치 | `git log --oneline HEAD --not --remotes=<원격>` | 없음 |

- 원격은 인자 → upstream의 원격 → `origin`. 브랜치는 인자 → 현재 브랜치.
- 커밋하지 않은 변경은 push되지 않는다고 알린다(커밋하지 않는다).
- 올라갈 커밋 목록을 보여 준다. 이번 작업과 무관해 보이는 커밋이 섞여 있으면 묻는다.

## 2. 막는 경우

- **force push**(`--force`, `--force-with-lease`)는 하지 않는다. 사용자가 명시적으로 요청해도, 덮어쓸 원격 커밋 목록을 보여 주고 다시 확인받은 뒤 `--force-with-lease`만 쓴다. 보호·배포 브랜치에는 하지 않는다.
- **보호·배포 브랜치**(`git.md`에 적힌 것, 없으면 `main`·`master`·`release/*`·`prod*`)로의 직접 push 요청이면 멈추고 알린다. 저장소 흐름상 PR/MR로 합치는 브랜치면 `devkit:pr-publish`를 제안한다.
- pre-push 훅이 실패하면 원인을 보고한다(`--no-verify`·force는 devkit 가드 훅이 막는다).

## 3. 원격이 앞서 있을 때

원격에만 있는 커밋이 있으면 push하지 않고 목록을 보여 준 뒤 합칠 방법을 묻는다. 권장은 `git.md`를 따르고, 없으면 merge(`git merge <원격>/<브랜치>`)를 권장안으로 둔다. rebase는 이미 공유된 커밋을 다시 쓰므로 사용자가 고를 때만 한다. 충돌이 나면 충돌 파일을 보여 주고 지시를 받는다.

## 4. push

```bash
git push <원격> <브랜치>            # upstream 있음
git push -u <원격> <브랜치>         # 새 브랜치
git log -1 --format=%H <원격>/<브랜치>
```

## 5. 보고

원격·브랜치·올라간 커밋 범위(SHA)·새 브랜치 여부를 알린다. CI 설정상 이 push로 파이프라인·배포가 도는 브랜치면 그 점을 함께 알린다. PR/MR은 요청받으면 `devkit:pr-publish`로 한다.
