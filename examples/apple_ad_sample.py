# -*- coding: utf-8 -*-
FORMAT = "apple_ad"
SCENES = [
    dict(layout="word", text="가볍다", sub="그리고 단단하다",
         narration="가볍다. 그리고 단단하다.", hold=1.2),
    dict(layout="spec", value="38", unit="일", note="아무도 몰랐던 시간",
         narration="서른여덟 날.", hold=1.2),
    dict(layout="phrase", text="당신이 믿은 것은 무엇입니까",
         narration="당신이 믿은 것은 무엇입니까.", hold=1.4),
    dict(layout="blackout", text="그리고",
         narration="", hold=1.0),
    dict(layout="logo", text="건규채널", tag="알고 나면 달라 보이는 것들",
         narration="", hold=1.8),
]
FPS = 30
W, H = 1920, 1080
