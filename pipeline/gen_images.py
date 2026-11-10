#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""이미지 프롬프트 파일 -> 생성된 이미지.

    python pipeline/gen_images.py --prompts work/image_prompts.md --out assets/

codex 의 내장 `image_gen` 에 위임한다. 구독으로 동작하므로 API 키가 필요 없다.
codex 가 없으면 그 사실을 알리고 종료한다 — 없는데 만든 척하지 않는다.

프롬프트 파일 형식 (비주얼 에이전트가 쓰는 그대로):

    ### `s01_server.jpg`
    A dark server room corridor at night, ...

    ### `s02_desk.jpg`
    A single desk lit only by a monitor, ...
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SUFFIX = """
Cinematic still, 16:9. Single light source in deep darkness, most of the frame
near-black. Muted desaturated palette with one warm accent. Shallow depth of
field, fine film grain. Photographic realism. Absolutely no text, no letters,
no numbers, no logos, no watermarks. No recognizable faces. Leave the lower
third dark and uncluttered.
"""


def parse(path):
    """### `파일명` 다음에 오는 문단을 프롬프트로 읽는다."""
    items, name, buf = [], None, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,4}\s*`?([\w./-]+\.(?:jpg|jpeg|png))`?\s*$", line.strip())
        if m:
            if name and buf:
                items.append((name, "\n".join(buf).strip()))
            name, buf = m.group(1), []
        elif name and line.strip() and not line.startswith("#"):
            buf.append(line.strip())
    if name and buf:
        items.append((name, "\n".join(buf).strip()))
    return items


def main():
    ap = argparse.ArgumentParser(description="codex image_gen 으로 이미지 생성")
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", default="assets")
    ap.add_argument("--suffix", default=None, help="공통 스타일 접미사 덮어쓰기")
    args = ap.parse_args()

    if not shutil.which("codex"):
        raise SystemExit(
            "codex CLI 가 없습니다. 이미지 생성을 건너뜁니다.\n"
            "  · 타이포만으로 가거나\n"
            "  · 직접 만든 이미지를 assets/ 에 넣으세요 (프롬프트는 "
            + args.prompts + " 에 있습니다)")

    items = parse(args.prompts)
    if not items:
        raise SystemExit("프롬프트를 찾지 못했습니다. '### `파일명.jpg`' 형식인지 확인하세요.")

    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    suffix = args.suffix if args.suffix is not None else SUFFIX

    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    task = work / "_imagegen_task.md"
    lines = [
        "# 작업 지시", "",
        "**반드시 내장 `image_gen` 도구를 쓴다.** 외부 API 나 스크립트를 쓰지 않는다.", "",
        "- 저장 위치: `%s`" % out.as_posix(),
        "- 파일명은 아래 지정 그대로. 가로세로비 16:9, 최소 1920x1080",
        "- 각 프롬프트 뒤에 아래 공통 스타일을 붙여서 생성한다", "",
        "```", suffix.strip(), "```", "",
        "**이미지 안에 글자가 들어가면 안 된다.** 자막은 영상 쪽에서 얹는다.", "",
        "## 생성할 이미지 %d장" % len(items), "",
    ]
    for name, prompt in items:
        lines += ["### `%s`" % name, prompt, ""]
    lines += ["## 끝나면", "생성한 파일의 실제 경로와 크기를 목록으로 보고한다."]
    task.write_text("\n".join(lines), encoding="utf-8")

    print("이미지 %d장 생성 요청 -> %s" % (len(items), out))
    r = subprocess.run(
        ["codex", "exec", "--sandbox", "workspace-write", "-C", str(ROOT),
         "Read %s (UTF-8) and do exactly what it says. Use the built-in image_gen "
         "tool to generate every image and save them with the exact filenames given. "
         "Report the final file paths and sizes." % task.relative_to(ROOT).as_posix()],
        text=True)
    if r.returncode != 0:
        raise SystemExit("codex 실행이 실패했습니다.")

    made = sorted(p.name for p in out.glob("*.jpg")) + sorted(p.name for p in out.glob("*.png"))
    print("\n생성됨 (%d개):" % len(made))
    for m in made:
        print("  ", m)
    missing = [n for n, _ in items if n not in made]
    if missing:
        print("\n빠진 것:", ", ".join(missing))


if __name__ == "__main__":
    main()
