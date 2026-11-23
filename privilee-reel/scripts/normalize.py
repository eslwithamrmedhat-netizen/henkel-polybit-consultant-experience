#!/usr/bin/env python3
"""Pass 1 (correct/normalize) + Pass 2 (look) for every source used by any variant.

  python3 scripts/normalize.py            # process what's needed (skips up-to-date jobs)
  python3 scripts/normalize.py --force    # rebuild everything

Video: autorotate -> SDR Rec.709 (real HLG/PQ tone-map) -> CFR 30 fps (or native HFR
when a shot asks for slow motion) -> cover-size scale (never upscaled here) -> grade ->
H.264 CRF 12 intermediate with bt709 tags, original audio kept as AAC 48 kHz.
Stills: EXIF orientation + ICC (Display P3) -> sRGB -> scale -> grade -> JPEG q2.
Originals in media/ are only read. Writes processed/media/*, processed/media_map.json and
before/after grading sheets in qa/grade/.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from common import MEDIA, PROCESSED, QA, ROOT, ffprobe, load_json, open_image, run, save_json, sdr_chain, to_srgb, video_summary
from timeline import all_variant_names, grade_params, job_key, load_looks, load_timeline, resolve_shots

OUT = PROCESSED / "media"
MAP = PROCESSED / "media_map.json"
W, H, FPS = 1080, 1920, 30
HEADROOM = 1.12  # room for re-framing / slow push-ins without upscaling
HANDLE = 0.5


def grade_filters(g: dict) -> list[str]:
    f = []
    if g["tempMix"] > 0 and g["temperature"] != 6500:
        f.append(f"colortemperature=temperature={g['temperature']}:mix={g['tempMix']}:pl=1")
    s, m, h = g["shadows"], g["midtones"], g["highlights"]
    if any(s + m + h):
        f.append(f"colorbalance=rs={s[0]}:gs={s[1]}:bs={s[2]}:rm={m[0]}:gm={m[1]}:bm={m[2]}:rh={h[0]}:gh={h[1]}:bh={h[2]}:pl=1")
    if (g["contrast"], g["brightness"], g["saturation"], g["gamma"]) != (1.0, 0.0, 1.0, 1.0):
        f.append(f"eq=contrast={g['contrast']}:brightness={g['brightness']}:saturation={g['saturation']}:gamma={g['gamma']}")
    return f


def cover_size(w: int, h: int) -> tuple[int, int]:
    scale = min(1.0, max(W / w, H / h) * HEADROOM)
    return max(2, int(w * scale) // 2 * 2), max(2, int(h * scale) // 2 * 2)


def collect_jobs(tl: dict, looks: dict) -> dict:
    jobs: dict[str, dict] = {}
    for name in all_variant_names(tl):
        for shot in resolve_shots(tl, name):
            key = job_key(shot, looks)
            if not key:
                continue
            src = MEDIA / shot["src"]
            if not src.exists():
                raise SystemExit(f"Shot '{shot['id']}' points to missing file media/{shot['src']}")
            j = jobs.setdefault(key, {"src": shot["src"], "grade": grade_params(shot, looks), "kind": shot.get("kind", "video"), "start": 1e9, "end": 0.0, "slowmo": False, "shots": set()})
            j["shots"].add(shot["id"])
            if j["kind"] in ("video", "offer"):
                speed = float(shot.get("speed", 1.0))
                j["start"] = min(j["start"], float(shot.get("in", 0)))
                j["end"] = max(j["end"], float(shot.get("in", 0)) + float(shot["dur"]) * speed)
                j["slowmo"] |= speed < 1.0
    return jobs


def process_video(key: str, j: dict, hdr: dict) -> dict:
    src = MEDIA / j["src"]
    s = video_summary(ffprobe(src))
    start = max(0.0, j["start"] - HANDLE)
    end = min(s["duration"], j["end"] + HANDLE)
    dw, dh = s["display_size"]
    ow, oh = cover_size(dw, dh)
    fps = FPS
    if j["slowmo"] and (s.get("avg_fps") or 0) > FPS:
        fps = min(120, round(s["avg_fps"]))
    chain = sdr_chain(s, hdr) + [f"fps={fps}", f"scale={ow}:{oh}:flags=lanczos", "setsar=1"] + grade_filters(j["grade"]) + ["format=yuv420p"]
    out = OUT / f"{Path(j['src']).stem}__{key}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(src), "-vf", ",".join(chain),
           "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"] if s.get("audio") else ["-an"]
    cmd += ["-movflags", "+faststart", str(out)]
    run(cmd)
    return {"file": str(out.relative_to(PROCESSED)), "offset": round(start, 3), "fps": fps, "width": ow, "height": oh, "hasAudio": bool(s.get("audio")), "duration": round(end - start, 3), "source": s}


def process_image(key: str, j: dict) -> dict:
    src = MEDIA / j["src"]
    img, icc = open_image(src)
    img, note = to_srgb(img, icc)
    ow, oh = cover_size(*img.size)
    from PIL import Image

    img = img.resize((ow, oh), Image.LANCZOS)
    out = OUT / f"{Path(j['src']).stem}__{key}.jpg"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "in.png"
        img.save(tmp)
        vf = grade_filters(j["grade"])
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(tmp)] + (["-vf", ",".join(vf)] if vf else []) + ["-q:v", "2", str(out)]
        run(cmd)
    return {"file": str(out.relative_to(PROCESSED)), "width": ow, "height": oh, "colour": note}


def before_after(key: str, j: dict, entry: dict, hdr: dict) -> Path | None:
    """Side-by-side: pass-1 corrected (left) vs graded (right) at the middle of the used range."""
    from PIL import Image, ImageDraw

    gdir = QA / "grade"
    gdir.mkdir(parents=True, exist_ok=True)
    out = gdir / f"{Path(j['src']).stem}__{key}.jpg"
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.jpg", Path(td) / "b.jpg"
        if entry.get("offset") is not None and j["kind"] != "image":
            s = entry["source"]
            mid = (j["start"] + j["end"]) / 2
            chain = sdr_chain(s, hdr) + ["scale=480:-2"]
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{mid:.3f}", "-i", str(MEDIA / j["src"]), "-vf", ",".join(chain), "-frames:v", "1", str(a)])
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{mid - entry['offset']:.3f}", "-i", str(PROCESSED / entry["file"]), "-vf", "scale=480:-2", "-frames:v", "1", str(b)])
        else:
            img, icc = open_image(MEDIA / j["src"])
            img, _ = to_srgb(img, icc)
            img.thumbnail((480, 1000))
            img.save(a)
            run(["ffmpeg", "-v", "error", "-y", "-i", str(PROCESSED / entry["file"]), "-vf", "scale=480:-2", str(b)])
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        sheet = Image.new("RGB", (ia.width + ib.width + 24, max(ia.height, ib.height) + 40), (16, 16, 16))
        sheet.paste(ia, (8, 32))
        sheet.paste(ib, (16 + ia.width, 32))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), "pass 1: corrected", fill=(220, 220, 220))
        d.text((16 + ia.width, 8), f"pass 2: {j['grade']}"[:90], fill=(220, 220, 220))
        sheet.save(out, quality=90)
    return out


def grade_overview(paths: list[Path]) -> None:
    from PIL import Image

    if not paths:
        return
    ims = [Image.open(p) for p in paths]
    w = max(i.width for i in ims)
    sheet = Image.new("RGB", (w, sum(i.height for i in ims)), (16, 16, 16))
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height
    sheet.thumbnail((1400, 12000))
    sheet.save(QA / "grade" / "_overview.jpg", quality=88)


def main() -> None:
    force = "--force" in sys.argv
    tl, looks = load_timeline(), load_looks()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = collect_jobs(tl, looks)
    if not jobs:
        print("No shot has a src yet — fill config/timeline.json after the media audit. Nothing to normalize.")
        save_json(MAP, {})
        return
    old = load_json(MAP, {})
    new, sheets = {}, []
    for key, j in jobs.items():
        prev = old.get(key)
        fresh = prev and (PROCESSED / prev["file"]).exists() and (j["kind"] == "image" or (prev.get("offset", 0) <= max(0, j["start"] - HANDLE) + 1e-3 and prev["offset"] + prev["duration"] >= j["end"]))
        if fresh and not force:
            new[key] = prev
            print(f"=  {prev['file']}")
            continue
        entry = process_image(key, j) if j["kind"] == "image" else process_video(key, j, looks.get("hdr", {}))
        entry["shots"] = sorted(j["shots"])
        new[key] = entry
        sheets.append(before_after(key, j, entry, looks.get("hdr", {})))
        print(f"+  {entry['file']}  ({', '.join(entry['shots'])})")
    save_json(MAP, new)
    grade_overview([p for p in sheets if p])
    print(f"\n{len(new)} intermediates · map {MAP.relative_to(ROOT)} · grade sheets qa/grade/")


if __name__ == "__main__":
    main()
