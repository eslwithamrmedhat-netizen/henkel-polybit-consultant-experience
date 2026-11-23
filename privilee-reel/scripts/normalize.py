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
    """Pass 2 scene look, RGB domain only: light warmth/tint and a gentle contrast curve."""
    f = []
    if g["tempMix"] > 0 and g["temperature"] != 6500:
        f.append(f"colortemperature=temperature={g['temperature']}:mix={g['tempMix']}:pl=1")
    s, m, h = g["shadows"], g["midtones"], g["highlights"]
    if any(s + m + h):
        f.append(f"colorbalance=rs={s[0]}:gs={s[1]}:bs={s[2]}:rm={m[0]}:gm={m[1]}:bm={m[2]}:rh={h[0]}:gh={h[1]}:bh={h[2]}:pl=1")
    c = g["contrast"]
    if abs(c - 1.0) > 1e-3:
        lo, hi = 0.5 + (0.25 - 0.5) * c, 0.5 + (0.75 - 0.5) * c
        f.append(f"curves=all='0/0 0.25/{max(0.02, lo):.4f} 0.75/{min(0.98, hi):.4f} 1/1'")
    return f


# ---------------------------------------------------------------- pass 3: shot matching
# Every shot is measured after pass 1 and pulled toward one shared target (black/white point,
# midtone exposure, colour cast, saturation) BEFORE the light scene look is applied, so the
# sequence reads as one film instead of many phones and app filters. Strengths are partial on
# purpose: golden light and each gym's own lighting keep some of their character.
MATCH = {
    #               cast  sat_target  exposure_target
    "neutral":         (0.55, 0.30, 0.46),
    "work_city":       (0.55, 0.30, 0.47),
    "gym_indoor":      (0.40, 0.31, 0.45),
    "pool_beach":      (0.45, 0.34, 0.50),
    "golden_portrait": (0.25, 0.32, 0.45),
}


def measure(rgb_frames: list) -> dict:
    import numpy as np

    a = np.concatenate([f.reshape(-1, 3) for f in rgb_frames]).astype(np.float32) / 255.0
    y = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mx, mn = a.max(1), a.min(1)
    valid = mx > 0.08
    sat = float(np.mean(((mx - mn) / np.maximum(mx, 1e-3))[valid])) if valid.any() else 0.0
    mid = (y > 0.18) & (y < 0.82)
    cast = a[mid].mean(0) if mid.sum() > 500 else a.mean(0)
    return {
        "lo": [float(np.percentile(a[:, c], 0.5)) for c in range(3)],
        "hi": float(np.percentile(a.max(1), 99.6)),
        "y_mean": float(y.mean()),
        "sat": sat,
        "cast": [float(c) for c in cast],
    }


def match_filters(m: dict, g: dict) -> tuple[list[str], dict]:
    """Return RGB-domain FFmpeg filters that bring a measured shot to the shared target."""
    import math

    strength = float(g.get("match", 1.0))
    cast_k, sat_t, exp_t = MATCH.get(g.get("look", "neutral"), MATCH["neutral"])
    # black point per channel (also removes coloured shadow haze), common white point (keeps highlight colour)
    lo = [min(0.22, max(0.0, (l - 0.012) * 0.9 * strength)) for l in m["lo"]]
    hi = m["hi"]
    wmax = 1.0 if hi > 0.965 else max(0.78, 1.0 - (1.0 - (hi + (1 - hi) * 0.25)) * strength)
    f = [f"colorlevels=rimin={lo[0]:.4f}:gimin={lo[1]:.4f}:bimin={lo[2]:.4f}:rimax={wmax:.4f}:gimax={wmax:.4f}:bimax={wmax:.4f}"]
    # midtone cast toward neutral (partial, clamped)
    c = m["cast"]
    avg = sum(c) / 3
    gains = [max(0.9, min(1.1, (avg / max(ci, 1e-3)) ** (cast_k * strength))) for ci in c]
    # exposure (gamma) and saturation toward the shared target
    y = min(0.9, max(0.05, (m["y_mean"] - sum(lo) / 3) / max(0.2, wmax - sum(lo) / 3)))
    gamma = max(0.88, min(1.18, (math.log(y) / math.log(exp_t)) ** (0.6 * strength)))
    sat = max(0.72, min(1.22, (sat_t / max(m["sat"], 0.05)) ** (0.75 * strength)))
    gamma *= float(g.get("gamma", 1.0))
    sat *= float(g.get("saturation", 1.0))
    f.append(f"lutrgb=r=gammaval({1 / gamma:.4f}):g=gammaval({1 / gamma:.4f}):b=gammaval({1 / gamma:.4f})")
    # one matrix: BT.709-luma-preserving saturation, then per-channel white-balance gains
    w = (0.2126, 0.7152, 0.0722)
    rows = [[(1 - sat) * w[j] + (sat if i == j else 0.0) for j in range(3)] for i in range(3)]
    rows = [[v * gains[i] for v in rows[i]] for i in range(3)]
    names = ["r", "g", "b"]
    f.append("colorchannelmixer=" + ":".join(f"{names[i]}{names[j]}={rows[i][j]:.5f}" for i in range(3) for j in range(3)))
    return f, {"black": [round(x, 3) for x in lo], "white": round(wmax, 3), "wb_gains": [round(x, 3) for x in gains], "gamma": round(gamma, 3), "sat": round(sat, 3), "measured": {k: (round(v, 3) if isinstance(v, float) else [round(x, 3) for x in v]) for k, v in m.items()}}


def frames_for_measure(src: Path, chain: list[str], times: list[float]) -> list:
    import numpy as np
    from PIL import Image

    out = []
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            f = Path(td) / f"{i}.png"
            vf = ",".join(chain + ["scale=360:-2:in_color_matrix=bt709:out_color_matrix=bt709", "format=rgb24"])
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-vf", vf, "-frames:v", "1", str(f)], check=False)
            if f.exists():
                out.append(np.asarray(Image.open(f).convert("RGB")))
    return out


TO_RGB = "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=gbrp"
TO_YUV = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"


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
            from common import media_kind

            kind = "freeze" if shot.get("freeze") else (media_kind(src) or "video")
            j = jobs.setdefault(key, {"src": shot["src"], "grade": grade_params(shot, looks), "kind": kind, "at": float(shot.get("in", 0)), "start": 1e9, "end": 0.0, "slowmo": False, "shots": set()})
            j["shots"].add(shot["id"])
            if j["kind"] == "video":
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
    pass1 = sdr_chain(s, hdr)
    times = [j["start"] + (j["end"] - j["start"]) * k for k in (0.15, 0.5, 0.85)]
    mf, minfo = match_filters(measure(frames_for_measure(src, pass1, times)), j["grade"])
    chain = pass1 + [f"fps={fps}", f"scale={ow}:{oh}:flags=lanczos", "setsar=1", TO_RGB] + mf + grade_filters(j["grade"]) + [TO_YUV]
    out = OUT / f"{Path(j['src']).stem}__{key}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(src), "-vf", ",".join(chain),
           "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"] if s.get("audio") else ["-an"]
    cmd += ["-movflags", "+faststart", str(out)]
    run(cmd)
    return {"file": str(out.relative_to(PROCESSED)), "offset": round(start, 3), "fps": fps, "width": ow, "height": oh, "hasAudio": bool(s.get("audio")), "duration": round(end - start, 3), "source": s, "match": minfo}


def process_freeze(key: str, j: dict, hdr: dict) -> dict:
    """Freeze frame from a video: pass-1 corrected frame at j['at'], then graded like a photo."""
    from PIL import Image

    src = MEDIA / j["src"]
    s = video_summary(ffprobe(src))
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "f.png"
        vf = ",".join(sdr_chain(s, hdr) + ["scale=in_color_matrix=bt709:out_color_matrix=bt709", "format=rgb24"])
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{j['at']:.3f}", "-i", str(src), "-vf", vf, "-frames:v", "1", str(f)])
        img = Image.open(f).convert("RGB")
        img.load()
    entry = process_image(key, j, img=img, stem_suffix=f"_f{j['at']:.2f}")
    entry["freeze_at"] = j["at"]
    return entry


def process_image(key: str, j: dict, img=None, stem_suffix: str = "") -> dict:
    src = MEDIA / j["src"]
    if img is None:
        img, icc = open_image(src)
        img, note = to_srgb(img, icc)
    else:
        note = "freeze frame (Rec.709 SDR)"
    ow, oh = cover_size(*img.size)
    from PIL import Image

    img = img.resize((ow, oh), Image.LANCZOS)
    out = OUT / f"{Path(j['src']).stem}{stem_suffix}__{key}.jpg"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "in.png"
        img.save(tmp)
        import numpy as np

        small = img.copy()
        small.thumbnail((360, 640))
        mf, minfo = match_filters(measure([np.asarray(small.convert("RGB"))]), j["grade"])
        vf = ["format=gbrp"] + mf + grade_filters(j["grade"])
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(tmp)] + (["-vf", ",".join(vf)] if vf else []) + ["-q:v", "2", str(out)]
        run(cmd)
    return {"file": str(out.relative_to(PROCESSED)), "width": ow, "height": oh, "colour": note, "match": minfo}


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


def prepare_brand(tl: dict) -> None:
    """Brand assets are copied to processed/brand/ UNGRADED (proportions and colours preserved)."""
    out = PROCESSED / "brand"
    out.mkdir(parents=True, exist_ok=True)
    for sid, shot in tl["shots"].items():
        if shot.get("kind") == "phone":
            ui = out / "ui"
            ui.mkdir(exist_ok=True)

            def put(src: str, crop=None, name=None):
                img, icc = open_image(MEDIA / src)
                img, _ = to_srgb(img, icc)
                if crop:
                    w, h = img.size
                    img = img.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
                img.save(ui / ((name or Path(src).stem) + ".png"))

            put(shot["home"]["src"])
            put(shot["home"]["src"], shot["iconRect"], "privilee_icon")
            put(shot["splash"]["src"], shot["splash"].get("crop"))
            for sc in shot["screens"]:
                put(sc["src"], sc.get("crop"))
        if shot.get("kind") == "brand" and shot.get("src"):
            img, icc = open_image(MEDIA / shot["src"])
            img, _ = to_srgb(img, icc)
            img.save(out / (Path(shot["src"]).stem + ".png"))
    art = (load_json(ROOT / "config" / "offer.json", {}) or {}).get("artwork") or {}
    if art.get("file") and art.get("source"):
        img, icc = open_image(ROOT / art["source"])
        img, _ = to_srgb(img, icc)
        x0, y0, x1, y1 = art.get("crop", [0, 0, 1, 1])
        w, h = img.size
        img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).save(PROCESSED / art["file"])


def main() -> None:
    force = "--force" in sys.argv
    tl, looks = load_timeline(), load_looks()
    OUT.mkdir(parents=True, exist_ok=True)
    prepare_brand(tl)
    jobs = collect_jobs(tl, looks)
    if not jobs:
        print("No shot has a src yet — fill config/timeline.json after the media audit. Nothing to normalize.")
        save_json(MAP, {})
        return
    old = load_json(MAP, {})
    new, sheets = {}, []
    for key, j in jobs.items():
        prev = old.get(key)
        fresh = prev and (PROCESSED / prev["file"]).exists() and (j["kind"] in ("image", "freeze") or (prev.get("offset", 0) <= max(0, j["start"] - HANDLE) + 1e-3 and prev["offset"] + prev["duration"] >= j["end"]))
        if fresh and not force:
            new[key] = prev
            print(f"=  {prev['file']}")
            continue
        if j["kind"] == "freeze":
            entry = process_freeze(key, j, looks.get("hdr", {}))
        elif j["kind"] == "image":
            entry = process_image(key, j)
        else:
            entry = process_video(key, j, looks.get("hdr", {}))
        entry["shots"] = sorted(j["shots"])
        new[key] = entry
        if j["kind"] != "freeze":
            sheets.append(before_after(key, j, entry, looks.get("hdr", {})))
        print(f"+  {entry['file']}  ({', '.join(entry['shots'])})")
    save_json(MAP, new)
    grade_overview([p for p in sheets if p])
    print(f"\n{len(new)} intermediates · map {MAP.relative_to(ROOT)} · grade sheets qa/grade/")


if __name__ == "__main__":
    main()
