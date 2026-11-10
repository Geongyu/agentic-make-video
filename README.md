# agentic-make-video

글·자료·주제를 주면 **나레이션이 깔린 한국어 영상**을 만드는 에이전트 스킬.

영상 편집 프로그램을 쓰지 않는다. HTML/CSS 로 프레임을 그리고, TTS 로 나레이션을
만들고, ffmpeg 으로 합친다. 전부 코드라서 **문장 하나만 고쳐 1~2분 만에 다시 뽑을 수 있다.**

Claude Code · Codex · Gemini(Antigravity) 어디서 켜도 동작한다.

---

## 쓰는 법

에이전트에게 자료를 주고 영상을 만들어 달라고 하면 된다.

```
이 글로 영상 하나 만들어줘
→ (스킬이 켜짐) 포맷·대상·남길 메시지·길이를 묻는다
→ 작가·감독·비주얼·사운드 에이전트가 기획안을 짠다
→ 회의록과 이미지 예시를 보여 주고 승인을 받는다
→ 만든다
```

승인 전에는 전체 렌더링을 시작하지 않는다. 수천 장 뽑고 나서 "다시"가 되면
시간과 토큰이 둘 다 낭비되기 때문이다.

## 설치

```bash
pip install -r pipeline/requirements.txt
python -m playwright install chromium
```

`ffmpeg` 이 PATH 에 있어야 한다. 한국어 글꼴(Pretendard 권장)이 없으면 글자가 □□ 로 깨진다.

### 스킬로 등록

**Claude Code**

```bash
mkdir -p ~/.claude/skills
cp -r agentic-make-video ~/.claude/skills/
```

**Codex** — 저장소 루트에 `AGENTS.md` 가 있어서 그대로 읽는다.

**Gemini / Antigravity**

```bash
mkdir -p ~/.gemini/antigravity-cli/skills
cp -r agentic-make-video ~/.gemini/antigravity-cli/skills/
```

## 포맷 세 가지

| | 이름 | 길이 | 성격 |
| --- | --- | --- | --- |
| 1 | `shorts` | 45~90초 | 좌하단 자막, 빠른 전개. 정보 전달 |
| 2 | `channel_e` | 90~150초 | 「지식채널e」풍. 가운데 정렬, 질문으로 열고 질문으로 닫는다 |
| 3 | `apple_ad` | 30~60초 | 예전 아이폰 광고풍. 흰 배경, 한 화면 한 단어, 여백 |

## 직접 돌리기

에이전트 없이 손으로도 된다.

```bash
cp pipeline/script_template.py work/script.py
# work/script.py 의 SCENES 를 채운다

python pipeline/build.py work/script.py --format channel_e --stills   # 정지 컷 먼저
python pipeline/build.py work/script.py --format channel_e            # 전체
```

결과는 `work/output/script.mp4`.

**정지 컷을 먼저 뽑아 눈으로 본다.** 장면당 한 장이라 몇 초면 끝나고,
글자 넘침·겹침이 여기서 다 걸러진다.

### 이미지

```bash
python pipeline/gen_images.py --prompts work/image_prompts.md --out assets/
```

codex 의 내장 `image_gen` 에 위임한다. **구독으로 동작해서 API 키가 필요 없다.**
codex 가 없으면 그 사실을 알리고 멈춘다 — 없는데 만든 척하지 않는다.

이미지 없이 타이포만으로도 성립한다. 「지식채널e」도 절반 이상이 검은 화면에 글자뿐이다.

### 음악

`music/` 에 음원을 넣으면 그걸 쓰고, **비워 두면 `pipeline/audio.py` 가 직접 친다.**

직접 치는 쪽이 기본이다. 특정 순간에 음악을 끊을 수 있기 때문이다 —
"그런데" 로 뒤집히는 장면에서 음악이 뚝 끊기는 것은 고정 음원으로 못 한다.

음원을 쓴다면 저작권을 직접 확인한다. **클래식이라고 무료가 아니다.**
악보는 공유재산이어도 *그 연주 녹음*에는 따로 권리가 있다.
안전한 곳: Musopen, YouTube 오디오 보관함, Pixabay Music.

## 구조

```
SKILL.md                  에이전트가 읽는 지시문
AGENTS.md                 codex 용 (SKILL.md 를 가리킨다)
agents/
  writer.md               작가 — 이야기 축
  director.md             감독 — 영상화 판단, 장면표
  visual.md               비주얼 — 화면 설계, 이미지 프롬프트
  sound.md                사운드 — 음악·효과음·무음
  reviewer.md             검수 (선택) — 완성본 비평
pipeline/
  build.py                TTS -> 프레임 -> mp4
  audio.py                배경음·효과음 합성
  gen_images.py           codex image_gen 위임
  script_template.py      대본 템플릿
  LAYOUTS.md              포맷별 쓸 수 있는 layout
  formats/
    shorts.html
    channel_e.html
    apple_ad.html
assets/                   이미지
music/                    음원 (비워 두면 직접 합성)
work/                     작업물 · 산출물
```

## 알아 둘 것

**나레이션은 TTS 가 읽을 글이다.** 숫자·영문을 읽는 대로 적는다.
`38일` → `서른여덟 날`, `AI` → `에이아이`. 화면에 뜨는 글자와 달라도 된다.

**속도를 후처리로 올리지 않는다.** 음높이가 올라가 기계음이 된다.
TTS 에게 처음부터 빠르게 읽히면 억양이 유지된 채 빨라진다. 기본값은 포맷마다 다르다
(`shorts` +40%, `channel_e` +15%, `apple_ad` +25%).

**같은 `work/build_*` 에 두 작업을 동시에 돌리지 않는다.** 락이 걸려 있다.
먼저 걸어 둔 작업이 나중 작업의 중간 프레임을 읽어 깨진 영상을 만든 적이 있다.

**프레임은 JPEG 로, 워커 여러 개로** 뽑는다. PNG 한 장이 1.5MB 라
3,000장이면 4.5GB 를 쓴다. 이 설정으로 18분 걸리던 것이 1분 20초가 됐다.

## 실제 사건을 다룬다면

- 확인된 것과 확인되지 않은 것을 나눈다. 추정은 추정이라고 적는다
- 출처를 화면 각주에 남긴다
- 조사 진행 중이면 그렇게 표시한다
- 실명이 들어가면 공개 범위를 확인한다. 발표장과 유튜브는 다르다
- 특정 개인(제보자·피해자)을 다룰 때 2차 가해가 되지 않는지 본다

## 라이선스

MIT. 편하게 쓰고 고쳐 쓰세요.
