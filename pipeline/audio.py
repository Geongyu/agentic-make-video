# -*- coding: utf-8 -*-
"""배경음과 효과음을 직접 합성한다.

남의 음원을 쓰면 저작권이 걸리므로 numpy 로 파형을 만든다.
지식채널e 의 사운드는 화려하지 않다. 낮은 드론 하나가 깔리고, 숫자가 나올 때
배를 치는 저음이 한 번 들어가고, 장이 바뀔 때 아주 작은 소리가 난다. 그게 전부다.
그래서 과하게 만들지 않는 것이 핵심이다.

구성
  bed   드론(근음+5도+옥타브) + 공기음. 막이 바뀔 때 음이 바뀐다
  sfx   숫자 등장 = 저음 임팩트, 장 구분 = 작은 틱, 결론 직전 = 라이저
  믹스  나레이션이 나올 때 bed 를 사이드체인으로 눌러 준다 (build.py 가 처리)
"""

import math

import numpy as np

SR = 48000


# ---------------------------------------------------------------- 도구


def _t(n):
    return np.arange(n, dtype=np.float64) / SR


def _env(n, attack, release, hold=None):
    """어택-홀드-릴리스 포락선."""
    e = np.ones(n)
    a = min(int(attack * SR), n)
    r = min(int(release * SR), n - a if n > a else 0)
    if a:
        e[:a] = np.linspace(0, 1, a) ** 2
    if r:
        e[n - r:] = np.linspace(1, 0, r) ** 2
    if hold is not None:
        h = int(hold * SR)
        if a + h < n - r:
            e[a + h:n - r] = np.linspace(1, 0.35, n - r - a - h)
    return e


def _onepole_lp(x, cutoff):
    """아주 단순한 1차 저역통과. 합성음의 날카로움을 깎는다."""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def _onepole_hp(x, cutoff):
    return x - _onepole_lp(x, cutoff)


def _soft(x):
    """부드러운 새추레이션. 디지털 클립을 막는다."""
    return np.tanh(x * 1.4) / 1.4


# ---------------------------------------------------------------- 배경 드론


def drone(dur, root=55.0, bright=0.0, seed=0):
    """근음 + 5도 + 옥타브를 아주 느리게 흔들며 쌓는다."""
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    out = np.zeros(n)

    # 배음 구성 — 1, 1.5(5도), 2(옥타브), 3
    for mult, gain, detune in ((1.0, 1.00, 0.0), (1.5, 0.42, 0.13),
                               (2.0, 0.30, -0.19), (3.0, 0.12, 0.27)):
        f = root * mult + detune
        # 느린 비브라토 — 생명감만 주고 티가 나면 안 된다
        vib = 1 + 0.0016 * np.sin(2 * math.pi * (0.07 + 0.013 * mult) * t + mult)
        out += gain * np.sin(2 * math.pi * f * vib * t + rng.random() * 6.28)

    # 공기음 — 아주 낮게 깐 필터드 노이즈
    air = _onepole_lp(rng.normal(0, 1, n), 420 + bright * 900)
    air = _onepole_hp(air, 90)
    out = out / 1.9 + air * (0.030 + 0.020 * bright)

    # 아주 느린 숨쉬기
    breath = 0.72 + 0.28 * (0.5 + 0.5 * np.sin(2 * math.pi * 0.045 * t - 1.2))
    out *= breath
    return _onepole_lp(out, 1100 + bright * 1800)


# ---------------------------------------------------------------- 효과음


def impact(level=1.0, seed=1):
    """숫자가 나타날 때의 저음 한 방. 북이 아니라 가슴을 누르는 쪽."""
    dur = 2.0
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)

    # 주파수가 떨어지는 사인 — 전형적인 서브 임팩트
    f = 92 * np.exp(-t * 7.0) + 38
    phase = 2 * math.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * 2.6)

    # 아주 짧은 트랜지언트
    click = _onepole_hp(rng.normal(0, 1, n), 1800) * np.exp(-t * 90) * 0.18

    # 뒤에 남는 울림
    tail = _onepole_lp(rng.normal(0, 1, n), 260) * np.exp(-t * 1.5) * 0.10
    return _soft((body + click + tail) * level)


def tick(level=1.0, seed=2):
    """장이 바뀔 때의 아주 작은 소리."""
    dur = 0.9
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    bell = (np.sin(2 * math.pi * 1180 * t) * 0.6 +
            np.sin(2 * math.pi * 1770 * t) * 0.25)
    bell *= np.exp(-t * 13)
    hiss = _onepole_hp(rng.normal(0, 1, n), 4000) * np.exp(-t * 55) * 0.10
    return (bell + hiss) * 0.30 * level


def riser(dur=2.4, level=1.0, seed=3):
    """결론 직전에 조용히 차오르는 소리."""
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, n)
    # 통과 대역을 서서히 올린다
    low = _onepole_lp(noise, 300)
    high = _onepole_lp(noise, 2600)
    mix = np.linspace(0, 1, n) ** 2
    out = low * (1 - mix) + high * mix
    out = _onepole_hp(out, 160)
    out *= (np.linspace(0, 1, n) ** 2.2) * 0.22 * level
    # 같이 올라가는 저음
    out += np.sin(2 * math.pi * np.cumsum(55 + 25 * np.linspace(0, 1, n)) / SR) \
        * (np.linspace(0, 1, n) ** 3) * 0.16 * level
    return out


def sweep_down(level=1.0, seed=4):
    """막이 끝날 때 아래로 빠지는 소리."""
    dur = 1.6
    n = int(dur * SR)
    t = _t(n)
    f = 700 * np.exp(-t * 2.4) + 45
    phase = 2 * math.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 2.0) * 0.18 * level


# ---------------------------------------------------------------- 트랙 조립


def _add(track, clip, at):
    i = int(at * SR)
    if i >= track.size:
        return
    j = min(track.size, i + clip.size)
    track[i:j] += clip[:j - i]


def build_bed(scenes, total, acts=None):
    """장면 길이에 맞춰 드론을 깐다. 막이 바뀌면 음과 밝기를 바꾼다."""
    acts = acts or []
    n = int(total * SR)
    bed = np.zeros(n)

    # 막 경계(초) 목록 -> 구간별 근음
    bounds = [0.0] + [b for b in acts if 0 < b < total] + [total]
    roots = [55.00, 48.99, 58.27, 43.65, 55.00]   # A1, G1, A#1, F1, A1
    brights = [0.15, 0.0, 0.35, 0.55, 0.2]

    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        seg = b - a + 2.5                      # 다음 구간과 겹치게 꼬리를 길게
        d = drone(seg, root=roots[i % len(roots)],
                  bright=brights[i % len(brights)], seed=10 + i)
        d *= _env(d.size, attack=1.6, release=2.2)
        _add(bed, d, a)

    return bed * 0.5


def build_sfx(marks, total):
    """marks: [(초, 종류, 세기)] — 'impact' / 'tick' / 'riser' / 'down'"""
    n = int(total * SR)
    track = np.zeros(n)
    for k, (at, kind, lv) in enumerate(marks):
        if kind == "impact":
            _add(track, impact(lv, seed=100 + k), at)
        elif kind == "tick":
            _add(track, tick(lv, seed=200 + k), at)
        elif kind == "riser":
            _add(track, riser(2.4, lv, seed=300 + k), max(0.0, at - 2.4))
        elif kind == "down":
            _add(track, sweep_down(lv, seed=400 + k), at)
    return track


def write_wav(path, mono, peak=0.9):
    """모노 float -> 16bit 스테레오 wav."""
    x = np.asarray(mono, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    x = x / m * peak
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1).tobytes()

    import struct

    header = (b"RIFF" + struct.pack("<I", 36 + len(stereo)) + b"WAVEfmt " +
              struct.pack("<IHHIIHH", 16, 1, 2, SR, SR * 4, 4, 16) +
              b"data" + struct.pack("<I", len(stereo)))
    with open(path, "wb") as fh:
        fh.write(header + stereo)
    return path


# ---------------------------------------------------------------- 악보형 배경음
#
# 리뷰 지적: "나레이션 사이를 채우는 선율은 줄이고, 삭제·확인 순간에는 음악을 끊을
# 수 있어야 한다." 고정 녹음으로는 끊을 수 없어서 직접 친다.
# 정서는 비애가 아니라 의심 — 선율을 주지 않고 같은 음을 반복하는 맥박으로 간다.


def pluck(freq, dur=1.4, level=1.0, bright=1.0, seed=0):
    """마른 피아노 비슷한 한 음. 선율이 아니라 맥박으로 쓴다."""
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    # 배음마다 감쇠 속도를 달리해 금속성을 줄인다
    for k, g, dk in ((1, 1.00, 3.2), (2, 0.34, 5.0), (3, 0.15, 7.5),
                     (4.2, 0.07, 11.0)):
        out += g * np.sin(2 * math.pi * freq * k * t) * np.exp(-t * dk)
    # 타현음
    out += _onepole_hp(rng.normal(0, 1, n), 2600) * np.exp(-t * 120) * 0.05 * bright
    out *= np.minimum(1.0, t * SR / 120)          # 아주 짧은 어택
    return _onepole_lp(out, 2400 * bright) * 0.22 * level


def sub_note(freq, dur, level=1.0):
    """구간을 받쳐 주는 낮은 음."""
    n = int(dur * SR)
    t = _t(n)
    x = (np.sin(2 * math.pi * freq * t) * 1.0 +
         np.sin(2 * math.pi * freq * 2 * t) * 0.18)
    return x * _env(n, 1.2, 1.8) * 0.16 * level


def build_scored_bed(sections, total, bpm=72):
    """구간 목록대로 맥박을 친다.

    sections: [{start, end, root, density, level, pulse}]
      root     근음(Hz)
      density  한 박에 칠 확률 (0~1). 낮을수록 성기다
      pulse    False 면 저음만 깔고 맥박은 치지 않는다
    """
    n = int(total * SR)
    bed = np.zeros(n)
    beat = 60.0 / bpm

    for si, sec in enumerate(sections):
        a, b = sec["start"], sec["end"]
        if b <= a:
            continue
        root = sec.get("root", 110.0)
        lv = sec.get("level", 1.0)

        # 받침음
        _add(bed, sub_note(root / 2, b - a + 1.0, lv), a)

        if not sec.get("pulse", True):
            continue

        rng = np.random.default_rng(900 + si)
        k = 0
        at = a
        while at < b - 0.2:
            if rng.random() < sec.get("density", 0.5):
                # 같은 음을 반복하되 가끔 5도 위를 섞어 단조로움만 피한다
                f = root * (1.5 if (k % 8 == 5) else 1.0)
                vel = 0.75 + 0.25 * rng.random()
                if k % 4 == 0:
                    vel *= 1.25
                _add(bed, pluck(f, 1.5, lv * vel, bright=sec.get("bright", 1.0),
                                seed=si * 97 + k), at)
            at += beat
            k += 1

    return bed


def apply_cuts(track, cuts, fade=0.12):
    """지정 구간을 무음으로 만든다. (start, end) 초 목록."""
    for a, b in cuts:
        i, j = int(a * SR), int(min(b, track.size / SR) * SR)
        if j <= i:
            continue
        f = int(fade * SR)
        if i - f > 0:
            track[i - f:i] *= np.linspace(1, 0, f)
        track[i:j] = 0.0
        if j + f < track.size:
            track[j:j + f] *= np.linspace(0, 1, f)
    return track


def dry_hit(level=1.0, seed=7):
    """확인의 순간. 폭발음이 아니라 건조한 한 번."""
    dur = 1.1
    n = int(dur * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    body = np.sin(2 * math.pi * 148 * t) * np.exp(-t * 9.0)
    wood = _onepole_lp(rng.normal(0, 1, n), 1500) * np.exp(-t * 42) * 0.22
    return _soft((body + wood) * 0.5 * level)
