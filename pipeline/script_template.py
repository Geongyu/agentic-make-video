# -*- coding: utf-8 -*-
"""대본 템플릿. work/script.py 로 복사해서 쓴다.

장면은 dict 의 리스트다. 쓸 수 있는 layout 은 LAYOUTS.md 참조.

  narration   TTS 가 읽을 글. 숫자·영문은 읽는 대로 (38일 -> 서른여덟 날)
  hold        나레이션이 끝난 뒤 더 머무는 시간(초). 최소 0.6
  image       assets/ 안의 파일명
  image_focus 이미지에서 보여 줄 세로 위치 (0 위 ~ 100 아래, 기본 45)
  accent      강조 색 (red / amber / emerald)
  cut_music   True 면 그 장면 동안 배경음을 끊는다
  dry         True 면 건조한 타격음 한 번
  no_impact   True 면 숫자 장면이어도 저음 임팩트를 넣지 않는다
"""

FORMAT = "channel_e"          # shorts / channel_e / apple_ad

SCENES = [
    dict(layout="brand", tag="부제를 여기에", no_mark=True,
         narration="", hold=1.8),

    dict(layout="ask", label="질문",
         text="여기에 영상 전체를 여는 질문을 적는다.",
         narration="여기에 영상 전체를 여는 질문을 적는다.", hold=1.5),

    dict(layout="chapter", no="하나", title="첫 번째 막",
         narration="", hold=1.3),

    dict(layout="say", pre="사실을 한 문장으로 쌓는다.",
         narration="사실을 한 문장으로 쌓는다.", hold=0.9),

    dict(layout="say", pre="그런데 ", em="여기서 뒤집힌다", post=".",
         accent="red", cut_music=True, dry=True,
         narration="그런데 여기서 뒤집힌다.", hold=1.5),

    dict(layout="big", pre="숫자 위의 설명", value="38", unit="일",
         post="숫자 아래의 의미",
         caption="출처를 여기에",
         narration="서른여덟 날이었습니다.", hold=1.3),

    dict(layout="ask", label="다시, 질문",
         text="처음 질문으로 돌아온다.",
         narration="처음 질문으로 돌아온다.", hold=2.0),

    dict(layout="brand", tag="출처 · 기준일", no_mark=True,
         narration="", hold=2.4),
]

# ---- 선택: 기본값을 덮어쓸 때만 ----
# NARRATION_RATE = "+15%"
# VOICE = "ko-KR-InJoonNeural"      # 여성은 ko-KR-SunHiNeural
# MUSIC_VOLUME = 0.17
# SFX_VOLUME = 0.5
FPS = 30
W, H = 1920, 1080
