#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""대본 -> 영상.

    python pipeline/build.py work/script.py --format channel_e --stills
    python pipeline/build.py work/script.py --format channel_e
    python pipeline/build.py work/script.py --format shorts -o work/output/a.mp4

흐름
  1) 장면마다 나레이션을 TTS 로 만들고 길이를 잰다 -> 장면 길이가 거기서 나온다
  2) formats/<포맷>.html 을 Playwright 로 띄우고 프레임마다 캡처한다
  3) 배경음·효과음을 만들어 ffmpeg 으로 합친다

프레임은 JPEG 로 뽑고 워커 여러 개로 나눈다. PNG 한 장이 1.5MB 라
3,000장이면 디스크에서 막힌다.
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

FADE_IN = 0.45
FADE_OUT = 0.45
LEAD = 0.25          # 나레이션 시작 전 여유
LAST_HOLD_EXTRA = 0.6

FORMATS = ("shorts", "channel_e", "apple_ad")

# 포맷별 기본 나레이션 속도. channel_e 는 호흡이 길어 느리게 간다.
DEFAULT_RATE = {"shorts": "+40%", "channel_e": "+15%", "apple_ad": "+25%"}


def load_env():
    """work/.env 또는 .env 가 있으면 읽어 환경변수로 올린다."""
    for cand in (ROOT / ".env", ROOT / "work" / ".env"):
        if not cand.exists():
            continue
        for raw in cand.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw and not raw.startswith("#") and "=" in raw:
                k, v = raw.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


load_env()


# ---------------------------------------------------------------- 대본 읽기


def load_script(path):
    """work/script.py 를 모듈로 읽는다."""
    import importlib.util

    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location("user_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not getattr(mod, "SCENES", None):
        raise SystemExit("대본에 SCENES 가 비어 있습니다: %s" % path)
    return mod


# ---------------------------------------------------------------- 음성


async def _edge_tts(text, path, voice, rate, pitch):
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(path))


def synth(text, path, cfg):
    asyncio.run(_edge_tts(text, path, cfg["voice"], cfg["rate"], cfg["pitch"]))


def duration_of(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def plan(scenes, cfg, audio_dir):
    """장면마다 나레이션을 만들고 길이를 확정한다."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, sc in enumerate(scenes):
        sc = dict(sc)
        narration = (sc.get("narration") or "").strip()
        apath, speech = None, 0.0
        if narration:
            apath = audio_dir / ("%03d.mp3" % i)
            if not apath.exists():
                synth(narration, apath, cfg)
            speech = duration_of(apath)
        dur = LEAD + speech + float(sc.get("hold", 0.8))
        if i == len(scenes) - 1:
            dur += LAST_HOLD_EXTRA
        sc["__dur"] = round(dur, 3)
        sc["__audio"] = str(apath) if apath else None
        sc["__speech"] = speech
        out.append(sc)
    return out


# ---------------------------------------------------------------- 사운드 큐


def sound_cues(planned, tone):
    """장면에서 음악 구간·효과음·무음 구간을 뽑는다."""
    sections, marks, cuts = [], [], []
    cursor = 0.0
    seg_starts = [0.0]
    HEAD = ("chapter", "brand", "ask", "dateline")

    for sc in planned:
        kind = sc.get("layout")
        start, dur = cursor, sc["__dur"]

        if kind in HEAD and start > 0.5:
            seg_starts.append(start)
        if kind == "chapter":
            marks.append((start + 0.2, "tick", 0.55))
        if sc.get("cut_music"):
            cuts.append((start, start + dur))
        if kind in ("number", "big") and not sc.get("no_impact"):
            marks.append((start + LEAD + 0.5, "impact", 1.0))
        if sc.get("dry"):
            marks.append((start + LEAD + 0.25, "dry", 1.0))

        cursor += dur

    total = cursor
    seg_starts = sorted(set(seg_starts)) + [total]
    for i in range(len(seg_starts) - 1):
        t = tone[i % len(tone)]
        sections.append(dict(start=seg_starts[i], end=seg_starts[i + 1], **t))
    return sections, marks, cuts


def find_music_file():
    folder = ROOT / "music"
    if not folder.exists():
        return None
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg"):
        hits = sorted(folder.glob(ext))
        if hits:
            return hits[0]
    return None


def make_music(planned, total, tone, out_dir):
    import audio

    sections, marks, cuts = sound_cues(planned, tone)

    plain = [(t, k, lv) for t, k, lv in marks if k != "dry"]
    sfx = audio.build_sfx(plain, total)
    for t, k, lv in marks:
        if k == "dry":
            clip = audio.dry_hit(lv)
            i = int(t * audio.SR)
            j = min(sfx.size, i + clip.size)
            if j > i:
                sfx[i:j] += clip[:j - i]
    sfx_p = audio.write_wav(str(out_dir / "sfx.wav"), sfx, peak=0.9)

    track = find_music_file()
    if track:
        bed_p = out_dir / "bed.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(track), "-t", "%.3f" % total,
             "-af", "afade=t=in:st=0:d=2.5,afade=t=out:st=%.3f:d=3.0" % max(0.0, total - 3.0),
             "-ac", "2", "-ar", "48000", str(bed_p)], check=True, capture_output=True)
        print("   배경음: %s · 효과음 %d개" % (track.name, len(marks)))
        return str(bed_p), sfx_p

    bed = audio.build_scored_bed(sections, total, bpm=72)
    bed = audio.apply_cuts(bed, cuts)
    bed_p = audio.write_wav(str(out_dir / "bed.wav"), bed, peak=0.85)
    print("   맥박 %d구간 · 효과음 %d개 · 무음 %d구간"
          % (len(sections), len(marks), len(cuts)))
    return bed_p, sfx_p


# ---------------------------------------------------------------- 프레임 캡처


def frame_jobs(planned, fps, stills_only):
    jobs, total = [], 0
    for sc in planned:
        if stills_only:
            # 나레이션이 없는 장면은 등장 애니메이션이 늦게 끝나므로
            # 장면 중후반을 찍어야 완성된 화면이 나온다
            times = [max(0.0, min(sc["__dur"] - 0.05,
                                  max(LEAD + sc["__speech"] * 0.6 + 0.4,
                                      sc["__dur"] * 0.65)))]
        else:
            n = max(1, int(round(sc["__dur"] * fps)))
            times = [k / fps for k in range(n)]
        for t in times:
            jobs.append((total, sc, t))
            total += 1
    return jobs


def render_range(jobs, lo, hi, fade_out, html, frames_dir, w, h):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb",
                                           "--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(Path(html).as_uri())
        page.wait_for_function("window.__ready === true")
        page.wait_for_timeout(500)
        for idx, sc, t in jobs[lo:hi]:
            page.evaluate("([sc,t,fi,fo]) => window.renderFrame(sc,t,fi,fo)",
                          [sc, t, FADE_IN, fade_out])
            page.screenshot(path=str(Path(frames_dir) / ("f%06d.jpg" % idx)),
                            type="jpeg", quality=93)
        browser.close()


def _worker_main():
    spec = json.loads(Path(sys.argv[sys.argv.index("--worker") + 1]).read_text(encoding="utf-8"))
    jobs = [(j[0], j[1], j[2]) for j in spec["jobs"]]
    render_range(jobs, spec["lo"], spec["hi"], spec["fade_out"],
                 spec["html"], spec["frames"], spec["w"], spec["h"])


def capture(planned, cfg, out_dir, stills_only=False, workers=None):
    """프레임을 캡처한다. build/ 를 두 작업이 동시에 쓰지 못하게 락을 둔다."""
    frames = out_dir / "frames"
    lock = out_dir / ".render.lock"
    if lock.exists():
        raise SystemExit("이미 렌더가 돌고 있습니다 (%s). 끝나길 기다리거나 "
                         "확실히 멈췄다면 이 파일을 지우세요." % lock)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames.mkdir(parents=True, exist_ok=True)
    for old in list(frames.glob("*.jpg")) + list(frames.glob("*.png")):
        old.unlink()
    lock.write_text(str(os.getpid()), encoding="utf-8")

    try:
        jobs = frame_jobs(planned, cfg["fps"], stills_only)
        fade_out = 0 if stills_only else FADE_OUT
        html = str(HERE / "formats" / (cfg["format"] + ".html"))
        workers = workers or max(1, min(6, (os.cpu_count() or 4) - 2))

        if len(jobs) < workers * 20:
            render_range(jobs, 0, len(jobs), fade_out, html, frames, cfg["w"], cfg["h"])
            return len(jobs)

        serial = [[j[0], j[1], j[2]] for j in jobs]
        chunk = (len(jobs) + workers - 1) // workers
        procs, specs = [], []
        for wi in range(workers):
            lo, hi = wi * chunk, min((wi + 1) * chunk, len(jobs))
            if lo >= hi:
                break
            f = out_dir / ("plan_%d.json" % wi)
            f.write_text(json.dumps({"jobs": serial, "lo": lo, "hi": hi,
                                     "fade_out": fade_out, "html": html,
                                     "frames": str(frames),
                                     "w": cfg["w"], "h": cfg["h"]}, default=str),
                         encoding="utf-8")
            specs.append(f)
            procs.append(subprocess.Popen([sys.executable, str(HERE / "build.py"),
                                           "--worker", str(f)], env=dict(os.environ)))
        print("   워커 %d개로 %d프레임 분할" % (len(procs), len(jobs)))
        for pr in procs:
            if pr.wait() != 0:
                raise SystemExit("프레임 캡처 워커가 실패했습니다. "
                                 "--stills 로 먼저 돌려 어느 장면이 깨지는지 보세요.")
        for f in specs:
            f.unlink(missing_ok=True)
        return len(jobs)
    finally:
        lock.unlink(missing_ok=True)


# ---------------------------------------------------------------- 합성


def mux(planned, cfg, out_dir, out_path, music=True):
    frames = out_dir / "frames"
    total = sum(sc["__dur"] for sc in planned)
    inputs, filters, narr = [], [], []
    cursor, idx = 0.0, 1

    for sc in planned:
        if sc["__audio"]:
            inputs += ["-i", sc["__audio"]]
            d = int((cursor + LEAD) * 1000)
            filters.append("[%d:a]adelay=%d|%d[a%d]" % (idx, d, d, idx))
            narr.append("[a%d]" % idx)
            idx += 1
        cursor += sc["__dur"]

    bed_i = sfx_i = None
    if music:
        bed_p, sfx_p = make_music(planned, total, cfg["tone"], out_dir)
        inputs += ["-i", str(bed_p)]; bed_i = idx; idx += 1
        inputs += ["-i", str(sfx_p)]; sfx_i = idx; idx += 1

    cmd = ["ffmpeg", "-y", "-framerate", str(cfg["fps"]),
           "-i", str(frames / "f%06d.jpg")] + inputs

    if narr:
        filters.append("%samix=inputs=%d:normalize=0[narr0]" % ("".join(narr), len(narr)))
        if music:
            filters.append("[narr0]asplit=2[narr][sc]")
            filters.append("[%d:a]volume=%.2f[bedv]" % (bed_i, cfg["music_volume"]))
            filters.append("[bedv][sc]sidechaincompress="
                           "threshold=0.025:ratio=9:attack=12:release=420:makeup=1[bedduck]")
            filters.append("[%d:a]volume=%.2f[sfxv]" % (sfx_i, cfg["sfx_volume"]))
            filters.append("[narr][bedduck][sfxv]amix=inputs=3:normalize=0:"
                           "dropout_transition=0,alimiter=limit=0.95,apad[aout]")
        else:
            filters.append("[narr0]apad[aout]")
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v"]

    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p",
            "-x264-params", "aq-mode=3:aq-strength=1.1", "-r", str(cfg["fps"]),
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
            "-t", "%.3f" % total, str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg 실패: " + r.stderr[-2000:])
    return out_path


# ---------------------------------------------------------------- CLI


DEFAULT_TONE = [
    dict(root=110.0, density=0.34, bright=0.75),
    dict(root=110.0, density=0.46, bright=0.85),
    dict(root=103.8, density=0.62, bright=1.00),
    dict(root=123.5, density=0.44, bright=0.95),
    dict(root=98.0, density=0.52, bright=0.85),
    dict(root=92.5, density=0.38, bright=0.70),
    dict(root=110.0, density=0.26, bright=0.60),
]


def main():
    ap = argparse.ArgumentParser(description="대본을 영상으로 빌드")
    ap.add_argument("script", help="대본 .py 경로")
    ap.add_argument("--format", default=None, choices=FORMATS)
    ap.add_argument("--stills", action="store_true", help="장면당 정지 컷 한 장만")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--rate", default=None, help='나레이션 속도 (예: "+40%%")')
    ap.add_argument("--voice", default=None)
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg 가 필요합니다.")

    mod = load_script(args.script)
    fmt = args.format or getattr(mod, "FORMAT", "channel_e")
    if fmt not in FORMATS:
        raise SystemExit("포맷은 %s 중 하나여야 합니다." % ", ".join(FORMATS))

    cfg = {
        "format": fmt,
        "fps": getattr(mod, "FPS", 30),
        "w": getattr(mod, "W", 1920),
        "h": getattr(mod, "H", 1080),
        "voice": args.voice or getattr(mod, "VOICE", "ko-KR-InJoonNeural"),
        "rate": args.rate or getattr(mod, "NARRATION_RATE", DEFAULT_RATE[fmt]),
        "pitch": getattr(mod, "PITCH", "-2Hz"),
        "tone": getattr(mod, "TONE", DEFAULT_TONE),
        "music_volume": getattr(mod, "MUSIC_VOLUME", 0.17),
        "sfx_volume": getattr(mod, "SFX_VOLUME", 0.5),
    }

    name = Path(args.script).stem
    out_dir = ROOT / "work" / ("build_%s" % fmt)
    print("1) 나레이션 합성 (%s, %s)" % (cfg["voice"], cfg["rate"]))
    planned = plan(mod.SCENES, cfg, out_dir / "audio")
    total = sum(s["__dur"] for s in planned)
    print("   %d장면 · %.1f초" % (len(planned), total))

    print("2) 프레임 캡처 [%s]" % fmt)
    n = capture(planned, cfg, out_dir, args.stills, args.workers)
    print("   %d프레임" % n)
    if args.stills:
        print("   정지 컷: %s" % (out_dir / "frames"))
        return

    print("3) 합성")
    out = Path(args.output) if args.output else (ROOT / "work" / "output" / ("%s.mp4" % name))
    out.parent.mkdir(parents=True, exist_ok=True)
    mux(planned, cfg, out_dir, out, music=not args.no_music)
    mb = out.stat().st_size / 1048576
    print("완료 -> %s  (%.1f초 · %.1fMB)" % (out, total, mb))


if __name__ == "__main__":
    if "--worker" in sys.argv:
        _worker_main()
    else:
        main()
