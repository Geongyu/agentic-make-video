# agentic-make-video

이 저장소는 **영상 만들기 스킬**이다. 작업 지시는 `SKILL.md` 에 있다.

영상 제작 요청을 받으면 **먼저 `SKILL.md` 를 읽고 그대로 따른다.**
역할별 지시문은 `agents/` 에, 쓸 수 있는 레이아웃은 `pipeline/LAYOUTS.md` 에 있다.

핵심만 먼저:

1. 환경 확인 (python / ffmpeg / numpy / playwright)
2. 사용자에게 포맷·대상·남길 메시지·길이를 묻는다 (자료는 먼저 읽고 묻는다)
3. 작가·감독·비주얼·사운드 **네 에이전트를 띄운다**
4. 회의록 + 이미지 예시로 **승인을 받는다** — 승인 전 전체 렌더링 금지
5. `pipeline/build.py` 로 만든다. `--stills` 를 먼저 돌려 눈으로 본다

Codex 로 돌고 있다면 이미지는 내장 `image_gen` 을 그냥 쓴다. API 키가 필요 없다.
