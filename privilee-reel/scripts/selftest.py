#!/usr/bin/env python3
"""End-to-end pipeline self-test on SYNTHETIC media (colour bars, an HLG test clip, tone
"narration"). Everything happens under qa/_selftest/ — it never touches media/, config/,
processed/ or output/, and nothing it makes is a deliverable.

  python3 scripts/selftest.py
"""
from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ST = ROOT / "qa" / "_selftest"
DIRS = {k: ST / k.lower() for k in ("MEDIA", "AUDIO", "PROCESSED", "CONFIG", "QA", "OUTPUT")}


def sh(cmd: list[str]) -> None:
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f"$ {' '.join(cmd)}\n{r.stderr[-2000:]}")


def make_media() -> None:
    m = DIRS["MEDIA"]
    sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=6", "-f", "lavfi", "-i", "sine=f=330:d=6:sample_rate=48000",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(m / "test_portrait_sdr.mp4")])
    # 60 fps landscape HLG/BT.2020 10-bit test clip (exercises tone-mapping + framed layout + HFR)
    sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "smptehdbars=s=1920x1080:r=60:d=5",
        "-vf", "zscale=tin=bt709:t=arib-std-b67:pin=bt709:p=bt2020:min=bt709:m=bt2020nc,format=yuv420p10le",
        "-c:v", "libx265", "-x265-params", "log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc", "-tag:v", "hvc1",
        "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", str(m / "test_landscape_hlg.mov")])
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (1500, 2000))
    d = ImageDraw.Draw(im)
    for y in range(2000):
        d.line([(0, y), (1500, y)], fill=(int(200 - y / 20), int(150 + y / 40), int(120 + y / 25)))
    d.text((80, 900), "SYNTHETIC TEST STILL", fill=(255, 255, 255))
    im.save(m / "test_still.jpg", quality=92)


def make_narration(script_id: str, text: str) -> None:
    """Tone bursts per word + a fabricated-for-testing alignment (clearly not real speech)."""
    rate, t, chars, starts, ends, frames = 48000, 0.0, [], [], [], bytearray()
    for i, word in enumerate(text.split()):
        dur = 0.08 * len(word) + 0.1
        for c in word:
            chars.append(c)
            starts.append(round(t, 3))
            t += dur / len(word)
            ends.append(round(t, 3))
        n = int(dur * rate)
        frames += b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * k / rate))) for k in range(n))
        gap = 0.35 if word[-1] in ".,:" else 0.08
        chars.append(" ")
        starts.append(round(t, 3))
        t += gap
        ends.append(round(t, 3))
        frames += b"\x00\x00" * int(gap * rate)
    (DIRS["PROCESSED"] / "audio").mkdir(parents=True, exist_ok=True)
    with wave.open(str(DIRS["PROCESSED"] / "audio" / f"{script_id}.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate), w.writeframes(bytes(frames))
    (DIRS["PROCESSED"] / "alignment").mkdir(parents=True, exist_ok=True)
    json.dump({"alignment": {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends}},
              open(DIRS["PROCESSED"] / "alignment" / f"{script_id}.json", "w"))


def make_music() -> Path:
    out = DIRS["AUDIO"] / "test_pad.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=110:d=60:sample_rate=48000", "-f", "lavfi", "-i", "sine=f=165:d=60:sample_rate=48000",
        "-filter_complex", "amix=inputs=2,volume=0.4", str(out)])
    dst = DIRS["PROCESSED"] / "audio" / "music_test_pad.wav"
    shutil.copy2(out, dst)
    return dst


def main() -> None:
    if ST.exists():
        shutil.rmtree(ST)
    for d in DIRS.values():
        d.mkdir(parents=True)
    shutil.copytree(ROOT / "processed" / "fonts", DIRS["PROCESSED"] / "fonts")
    for f in ("looks.json", "platforms.json", "offer.json", "voiceover.json", "renders.json"):
        shutil.copy2(ROOT / "config" / f, DIRS["CONFIG"] / f)
    tl = json.load(open(ROOT / "config" / "timeline.json"))
    for sid, s in tl["shots"].items():
        if s["kind"] == "image":
            s["src"] = "test_still.jpg"
        elif s["kind"] in ("video", "offer"):
            s["src"] = "test_portrait_sdr.mp4"
    tl["shots"]["gym_b_match"].update({"src": "test_landscape_hlg.mov", "layout": "framed", "speed": 0.5, "in": 1.0})
    tl["locationLabels"] = [{"shot": "gym_a_action", "text": "Test label", "verified": True, "evidence": "selftest"},
                            {"shot": "gym_c_action", "text": "Must NOT render", "verified": False}]
    json.dump(tl, open(DIRS["CONFIG"] / "timeline.json", "w"), indent=2)
    spec = json.load(open(DIRS["CONFIG"] / "renders.json"))
    spec["music"].update({"file": "audio/music_test_pad.wav", "licence": "SELFTEST synthetic tone — not a real track"})
    json.dump(spec, open(DIRS["CONFIG"] / "renders.json", "w"), indent=2)

    make_media()
    vo = json.load(open(ROOT / "config" / "voiceover.json"))["scripts"]
    for sid in ("vo_cutdown", "vo_white_friday", "vo_main"):
        make_narration(sid, vo[sid]["text"])
    make_music()

    env = {**os.environ, **{f"REEL_{k}": str(v) for k, v in DIRS.items()}}
    py = [sys.executable]
    steps = [
        ["scripts/normalize.py"],
        ["scripts/captions.py", "vo_cutdown"],
        ["scripts/captions.py", "vo_white_friday"],
        ["scripts/captions.py", "vo_main"],
        ["scripts/render_all.py", "cutdown_instagram", "white_friday_tiktok"],
        ["scripts/verify.py", str(DIRS["OUTPUT"])],
    ]
    for s in steps:
        print(f"\n### {' '.join(s)}", flush=True)
        r = subprocess.run(py + s, cwd=ROOT, env=env)
        if r.returncode:
            sys.exit(f"SELFTEST FAILED at {s[0]}")
    print(f"\nSELFTEST PASSED — artefacts in {ST.relative_to(ROOT)} (synthetic; delete freely)")


if __name__ == "__main__":
    main()
