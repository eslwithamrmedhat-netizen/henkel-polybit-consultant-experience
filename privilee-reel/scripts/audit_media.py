#!/usr/bin/env python3
"""Media audit: technical manifest + contact sheets + still thumbnails.

  python3 scripts/audit_media.py                    # audit everything in media/
  python3 scripts/audit_media.py --frame FILE SECS  # export one native-resolution frame to qa/frames/

Writes config/asset_manifest.json. Technical fields are refreshed on every run; editorial
fields (description, role, best_in/out, location*, issues, selected) are preserved so the
manifest can be edited by hand. GPS/creation metadata goes ONLY to the private sidecar
config/asset_metadata.private.json (gitignored) — use it as corroborating location
evidence, never as a public label on its own.
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import CONFIG, MEDIA, QA, ROOT, ffprobe, load_json, media_kind, open_image, run, save_json, sdr_chain, video_summary

MANIFEST = CONFIG / "asset_manifest.json"
PRIVATE = CONFIG / "asset_metadata.private.json"
SHEETS = QA / "contact_sheets"
THUMBS = QA / "thumbnails"
EDITORIAL = {
    "description": "",
    "role": "",  # personal hook | work context | gym variety | workout action | country coverage | pool/beach relaxation | closing portrait
    "best_in": None,
    "best_out": None,
    "location": None,
    "location_status": "unconfirmed",  # unconfirmed | confirmed
    "location_evidence": "",
    "issues": [],
    "selected": False,
}
ROLES_HINT = "personal hook | work context | gym variety | workout action | country coverage | pool/beach relaxation | closing portrait"


def frame_at(src: Path, t: float, out: Path, width: int | None, summary: dict) -> bool:
    chain = sdr_chain(summary)
    if width:
        chain.append(f"scale={width}:-2")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src)]
    if chain:
        cmd += ["-vf", ",".join(chain)]
    cmd += ["-frames:v", "1", "-q:v", "3", str(out)]
    return run(cmd, check=False).returncode == 0 and out.exists()


def contact_sheet(src: Path, summary: dict, out: Path, n: int = 12, cols: int = 4) -> None:
    from PIL import Image, ImageDraw, ImageFont

    dur = max(summary.get("duration", 0), 0.1)
    times = [dur * (i + 0.5) / n for i in range(n)]
    tiles = []
    tmp = out.parent / f".{out.stem}_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        f = tmp / f"{i:02d}.jpg"
        if frame_at(src, t, f, 300, summary):
            tiles.append((t, Image.open(f).convert("RGB")))
    if not tiles:
        return
    tw = 300
    th = max(im.height for _, im in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 8, rows * (th + 30) + 50), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(ROOT / "processed/fonts/Inter-Medium.otf"), 18)
    except OSError:
        font = ImageFont.load_default()
    d.text((8, 12), f"{src.name}  ·  {dur:.2f}s  ·  {summary['display_size'][0]}x{summary['display_size'][1]}  ·  {summary.get('avg_fps')} fps  ·  {summary['dynamic_range']}", fill=(235, 235, 235), font=font)
    for i, (t, im) in enumerate(tiles):
        x = 8 + (i % cols) * (tw + 8)
        y = 50 + (i // cols) * (th + 30)
        sheet.paste(im, (x, y))
        d.text((x, y + im.height + 4), f"{t:6.2f}s", fill=(200, 200, 200), font=font)
    sheet.save(out, quality=88)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def still_info(path: Path) -> tuple[dict, dict]:
    from PIL import ExifTags

    img, icc = open_image(path)
    exif = img.getexif()
    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    private = {"datetime": str(tags.get("DateTime", "")) or None}
    try:
        gps = exif.get_ifd(0x8825)
        if gps:
            private["gps_raw"] = {ExifTags.GPSTAGS.get(k, k): str(v) for k, v in gps.items()}
    except Exception:
        pass
    w, h = img.size
    return (
        {
            "decodable": True,
            "display_size": [w, h],
            "orientation": "portrait" if h > w else ("landscape" if w > h else "square"),
            "icc_profile": bool(icc),
            "dynamic_range": "SDR (still; HDR gain map, if any, ignored)",
        },
        private,
    )


def auto_issues(kind: str, s: dict) -> list[str]:
    out = []
    w, h = s.get("display_size", [0, 0])
    if min(w, h) and min(w, h) < 1080:
        out.append(f"short side {min(w, h)} px < 1080: upscaling needed for full-frame use")
    if s.get("orientation") == "landscape":
        out.append("landscape: crop to 9:16 loses ~68% of width — check action stays in frame or use framed layout")
    if kind == "video":
        if s.get("vfr_suspected"):
            out.append("variable frame rate suspected: conform to 30 fps CFR during normalize")
        if s.get("dynamic_range") in ("HLG", "PQ"):
            out.append(f"{s['dynamic_range']} HDR: tone-map to SDR Rec.709 (automatic in normalize)")
        if (s.get("avg_fps") or 0) >= 50:
            out.append(f"high frame rate ({s['avg_fps']} fps): real slow motion possible (set 'speed' < 1 on the shot)")
        if s.get("audio"):
            out.append("has audio: listen for copyrighted gym music before using clip sound")
    return out


def audit() -> None:
    files = [p for p in sorted(MEDIA.rglob("*")) if p.is_file() and media_kind(p) in ("video", "image")]
    if not files:
        print("media/ is empty — nothing to audit. Supply originals (see README 'Getting the media in').")
        return
    manifest = load_json(MANIFEST, {"assets": {}})
    private = load_json(PRIVATE, {})
    SHEETS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    for p in files:
        rel = str(p.relative_to(MEDIA))
        kind = media_kind(p)
        prev = manifest["assets"].get(rel, {})
        entry = {"path": f"media/{rel}", "type": kind}
        try:
            if kind == "video":
                probe = ffprobe(p)
                tech = video_summary(probe) if "error" not in probe else {"decodable": False, "error": probe["error"]}
                ftags = (probe.get("format") or {}).get("tags") or {}
                private[rel] = {k: v for k, v in ftags.items() if "location" in k.lower() or "creation" in k.lower() or k.lower().startswith("com.apple.quicktime.make")}
                if tech.get("decodable"):
                    sheet = SHEETS / f"{p.stem}.jpg"
                    contact_sheet(p, tech, sheet)
                    entry["contact_sheet"] = str(sheet.relative_to(ROOT))
            else:
                tech, priv = still_info(p)
                private[rel] = priv
                img, icc = open_image(p)
                from common import to_srgb

                img, _ = to_srgb(img, icc)
                img.thumbnail((540, 960))
                th = THUMBS / f"{p.stem}.jpg"
                img.save(th, quality=88)
                entry["thumbnail"] = str(th.relative_to(ROOT))
        except Exception as exc:
            tech = {"decodable": False, "error": str(exc)}
        entry["technical"] = tech
        entry["auto_issues"] = auto_issues(kind, tech) if tech.get("decodable") else ["NOT DECODABLE"]
        for k, v in EDITORIAL.items():
            entry[k] = prev.get(k, v)
        manifest["assets"][rel] = entry
        print(f"{'ok ' if tech.get('decodable') else 'ERR'} {rel:50s} {kind:5s} {tech.get('display_size')} {tech.get('duration', ''):>} {tech.get('dynamic_range', '')}")
    manifest["_readme"] = f"Technical fields are generated. Fill editorial fields after inspecting contact sheets/frames. role: {ROLES_HINT}. location_status must stay 'unconfirmed' unless evidence (user note or corroborated recognisable place) is recorded — a filename alone is not evidence."
    save_json(MANIFEST, manifest)
    save_json(PRIVATE, private)
    print(f"\nManifest: {MANIFEST.relative_to(ROOT)}  ·  contact sheets: qa/contact_sheets/  ·  thumbnails: qa/thumbnails/")


def export_frame(file: str, t: float) -> None:
    src = (MEDIA / file) if not Path(file).exists() else Path(file)
    out = QA / "frames" / f"{src.stem}_{t:07.2f}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    s = video_summary(ffprobe(src))
    frame_at(src, t, out, None, s)
    print(out)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--frame":
        export_frame(sys.argv[2], float(sys.argv[3]))
    else:
        audit()
