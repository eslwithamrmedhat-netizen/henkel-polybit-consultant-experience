#!/usr/bin/env python3
"""Verify RENDERED files (not the preview): ffprobe facts, loudness, black frames, QA frames.

  python3 scripts/verify.py [dir]     # default output/  ->  qa/verification.md + .json

For every MP4: real dimensions, duration, codec/profile, pix_fmt, constant frame rate,
colour tags, audio codec/rate/channels, integrated loudness + true peak (EBU R128),
black segments, and a frame sheet sampled at every shot middle, title and caption change
(qa/frames/<file>.jpg) for visual inspection. It cannot listen: the report says so.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from common import OUTPUT, PROCESSED, QA, ROOT, ffprobe, load_json, rate, run, save_json


def loudness(path: Path) -> dict:
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], check=False)
    tail = res.stderr[res.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", tail)
    return {"integrated_lufs": i.group(1) if i else None, "true_peak_dbtp": tp.group(1) if tp else None, "lra": lra.group(1) if lra else None}


def black_segments(path: Path) -> list[list[float]]:
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", "blackdetect=d=0.15:pic_th=0.97", "-an", "-f", "null", "-"], check=False)
    return [[float(a), float(b)] for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", res.stderr)]


def sample_times(props: dict | None, duration: float) -> list[tuple[float, str]]:
    if not props:
        return [(duration * (i + 0.5) / 16, "") for i in range(16)]
    fps = props["fps"]
    t = [((s["from"] + s["durationInFrames"] / 2) / fps, s["id"]) for s in props["shots"]]
    t += [((o["from"] + min(20, o["durationInFrames"] // 2)) / fps, o["type"]) for o in props["overlays"]]
    t += [((c["from"] + 5) / fps, "cap") for c in props["captions"]]
    t += [(0.05, "first"), (duration - 0.05, "last")]
    return sorted({(round(x, 2), lab) for x, lab in t if 0 <= x < duration})


def frame_sheet(path: Path, times: list[tuple[float, str]], out: Path) -> None:
    from PIL import Image, ImageDraw

    tiles = []
    with tempfile.TemporaryDirectory() as td:
        for i, (t, lab) in enumerate(times):
            f = Path(td) / f"{i:03d}.jpg"
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=216:384", str(f)], check=False)
            if f.exists():
                tiles.append((t, lab, Image.open(f).convert("RGB")))
    if not tiles:
        return
    cols = 10
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 222, rows * 410), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (t, lab, im) in enumerate(tiles):
        x, y = (i % cols) * 222, (i // cols) * 410
        sheet.paste(im, (x + 3, y + 3))
        d.text((x + 6, y + 390), f"{t:5.2f}s {lab}"[:34], fill=(230, 230, 230))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)


def check(path: Path, props_by_out: dict) -> dict:
    p = ffprobe(path)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"]["duration"])
    r = {
        "file": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "duration_s": round(dur, 3),
        "size": f"{v['width']}x{v['height']}",
        "video": f"{v['codec_name']} {v.get('profile', '')} {v.get('pix_fmt')}",
        "fps_r": rate(v.get("r_frame_rate")),
        "fps_avg": round(rate(v.get("avg_frame_rate")) or 0, 3),
        "colour": f"{v.get('color_primaries')}/{v.get('color_transfer')}/{v.get('color_space')}/{v.get('color_range')}",
        "audio": f"{a['codec_name']} {a.get('sample_rate')} Hz {a.get('channels')} ch" if a else "none",
        "faststart": None,
    }
    head = path.open("rb").read(200_000)
    r["faststart"] = head.find(b"moov") != -1 and (head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat"))
    if a:
        r.update(loudness(path))
    r["black_segments"] = black_segments(path)
    issues = []
    if r["size"] != "1080x1920":
        issues.append("not 1080x1920")
    if not r["video"].startswith("h264") or "yuv420p" not in r["video"]:
        issues.append("not H.264 yuv420p")
    if abs((r["fps_r"] or 0) - 30) > 0.01 or abs(r["fps_avg"] - 30) > 0.05:
        issues.append("not 30 fps CFR")
    if not r["colour"].startswith("bt709/bt709/bt709"):
        issues.append(f"colour tags {r['colour']}")
    if a and a.get("sample_rate") != "48000":
        issues.append("audio not 48 kHz")
    if a and r.get("true_peak_dbtp") not in (None, "-inf") and float(r["true_peak_dbtp"]) > -1.0:
        issues.append(f"true peak {r['true_peak_dbtp']} dBTP > -1")
    if not r["faststart"]:
        issues.append("moov not at start")
    r["issues"] = issues
    sheet = QA / "frames" / f"{path.stem}.jpg"
    frame_sheet(path, sample_times(props_by_out.get(path.name), dur), sheet)
    r["frame_sheet"] = str(sheet.relative_to(ROOT))
    return r


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    log = load_json(d / "render_log.json", {"results": []})
    props_by_out = {}
    for res in log["results"]:
        if res.get("render") in (None, "cover", "subtitles", "stem"):
            continue
        props_by_out[Path(res["file"]).name] = load_json(PROCESSED / "props" / f"{res['render']}.json")
    files = sorted(d.glob("*.mp4"))
    if not files:
        raise SystemExit(f"No MP4s in {d}")
    results = [check(f, props_by_out) for f in files]
    extra = [f for f in sorted(d.glob("*")) if f.suffix in (".jpg", ".srt")] + sorted((d / "stems").glob("*.wav"))
    others = [{"file": str(f.relative_to(ROOT)), "bytes": f.stat().st_size} for f in extra]
    save_json(QA / "verification.json", {"videos": results, "other": others})
    md = ["# Render verification", "", "Automated checks on the rendered files. **No listen-through was possible in this environment** — audition audio before publishing.", "",
          "| File | Size | Dur | Frame | Video | fps | Colour | Audio | LUFS | TP | Black | Issues |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        md.append(f"| `{r['file']}` | {r['bytes'] / 1e6:.1f} MB | {r['duration_s']:.2f}s | {r['size']} | {r['video']} | {r['fps_avg']} | {r['colour']} | {r['audio']} | {r.get('integrated_lufs', '–')} | {r.get('true_peak_dbtp', '–')} | {len(r['black_segments'])} | {'; '.join(r['issues']) or 'none'} |")
    if others:
        md += ["", "Other files:", ""] + [f"- `{o['file']}` — {o['bytes'] / 1e3:.0f} KB" for o in others]
    md += ["", "Frame sheets (sampled at every shot, title and caption change): `qa/frames/`."]
    (QA / "verification.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
