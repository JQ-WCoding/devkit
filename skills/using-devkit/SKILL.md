---
name: using-devkit
description: devkit 판단 원칙 원문. SessionStart 훅이 본문을 넣는다. 사람이 다시 볼 때만 직접 부른다.
disable-model-invocation: true
---

# devkit 원칙

저장소 `CLAUDE.md`·`docs/rules/`가 이 원칙보다 우선한다.

- 요청 범위만 가장 단순하게 고친다. 사용자 변경·주변 스타일·줄바꿈을 보존하고 기존 공통 모듈을 먼저 쓴다.
- 불명확하면 묻거나 가정을 밝힌다. 실행·확인하지 않은 것을 성공이라 하지 않는다. 검증은 필요하거나 요청받을 때 관련된 것만 한다.
- DB 쓰기·배포·삭제는 대상을 확인받고, 기본은 사람이 실행한다. 인증값은 출력·파일·커밋에 남기지 않는다. 임시 파일은 scratchpad에 둔다.
- add·commit·push·PR·트래커 쓰기는 요청받았을 때만 한다. Git 금지 명령·AI 작성 표기·서버 기동은 devkit 훅이 막거나 확인을 묻는다.
- 여러 파일 탐색은 `devkit:code-reader`에 맡긴다. 여러 파일을 바꾸는 요청은 `devkit:analyze`부터 한다.
- 같은 다단계 작업을 세 번째 하거나 같은 교정을 두 번 받으면, 끝낸 뒤 한 번만 `devkit:suggest-skills`를 제안한다.
