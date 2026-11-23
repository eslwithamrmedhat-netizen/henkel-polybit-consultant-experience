"""Shared helpers for the Privilee reel pipeline (stdlib + optional Pillow/pillow-heif)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# REEL_* overrides exist only so scripts/selftest.py can exercise the pipeline in a scratch dir.
MEDIA = Path(os.environ.get("REEL_MEDIA", ROOT / "media"))
AUDIO = Path(os.environ.get("REEL_AUDIO", ROOT / "audio"))
BRAND = ROOT / "brand"
PROCESSED = Path(os.environ.get("REEL_PROCESSED", ROOT / "processed"))
CONFIG = Path(os.environ.get("REEL_CONFIG", ROOT / "config"))
QA = Path(os.environ.get("REEL_QA", ROOT / "qa"))
OUTPUT = Path(os.environ.get("REEL_OUTPUT", ROOT / "output"))

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".hevc", ".avi", ".mkv", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".dng"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".aif", ".aiff"}
HDR_TRANSFERS = {"arib-std-b67": "HLG", "smpte2084": "PQ"}


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, text=True, capture_output=True)
    if check and res.returncode != 0:
        sys.stderr.write(f"\n$ {' '.join(cmd)}\n{res.stderr[-4000:]}\n")
        raise SystemExit(res.returncode)
    return res


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def media_kind(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "image"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def ffprobe(path: Path) -> dict:
    res = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], check=False)
    if res.returncode != 0:
        return {"error": res.stderr.strip()[-500:]}
    return json.loads(res.stdout)


def rate(value: str | None) -> float | None:
    if not value or value in ("0/0", "0"):
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def rotation_of(stream: dict) -> int:
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            return int(round(float(sd["rotation"])))
    tag = (stream.get("tags") or {}).get("rotate")
    return int(tag) if tag else 0


def video_summary(probe: dict) -> dict:
    """Technical fields for the asset manifest, incl. display orientation after rotation."""
    v = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")), None)
    a = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        return {"decodable": False}
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = rotation_of(v)
    dw, dh = (h, w) if abs(rot) % 180 == 90 else (w, h)
    afr, rfr = rate(v.get("avg_frame_rate")), rate(v.get("r_frame_rate"))
    transfer = v.get("color_transfer")
    return {
        "decodable": True,
        "codec": v.get("codec_name"),
        "duration": float(probe.get("format", {}).get("duration") or v.get("duration") or 0),
        "coded_size": [w, h],
        "display_size": [dw, dh],
        "orientation": "portrait" if dh > dw else ("landscape" if dw > dh else "square"),
        "rotation": rot,
        "avg_fps": round(afr, 3) if afr else None,
        "r_fps": round(rfr, 3) if rfr else None,
        "vfr_suspected": bool(afr and rfr and abs(afr - rfr) > 0.5),
        "pix_fmt": v.get("pix_fmt"),
        "bit_depth": v.get("bits_per_raw_sample"),
        "color_primaries": v.get("color_primaries"),
        "color_transfer": transfer,
        "color_space": v.get("color_space"),
        "color_range": v.get("color_range"),
        "dynamic_range": HDR_TRANSFERS.get(transfer or "", "SDR"),
        "audio": bool(a),
        "audio_codec": a.get("codec_name") if a else None,
        "audio_rate": int(a["sample_rate"]) if a and a.get("sample_rate") else None,
    }


def sdr_chain(summary: dict, hdr_cfg: dict | None = None) -> list[str]:
    """FFmpeg filters that bring a video to SDR Rec.709 (tv range) before grading.

    HLG/PQ: real tone mapping through linear light (zscale + tonemap) — not just relabelling.
    SDR with non-709 primaries (e.g. Display P3 / BT.2020 SDR): primaries conversion.
    Rec.709 SDR: untouched apart from tagging.
    """
    hdr_cfg = hdr_cfg or {"tonemap": "hable", "desat": 0, "npl": 100}
    prim = summary.get("color_primaries") or "bt709"
    if summary.get("dynamic_range") in ("HLG", "PQ"):
        tin = "arib-std-b67" if summary["dynamic_range"] == "HLG" else "smpte2084"
        pin = "bt2020" if prim in ("bt2020", "unknown", None) else prim
        return [
            f"zscale=tin={tin}:pin={pin}:min=bt2020nc:t=linear:npl={hdr_cfg.get('npl', 100)}",
            "format=gbrpf32le",
            "zscale=p=bt709",
            f"tonemap=tonemap={hdr_cfg.get('tonemap', 'hable')}:desat={hdr_cfg.get('desat', 0)}",
            "zscale=t=bt709:m=bt709:r=tv",
            "format=yuv420p",
        ]
    if prim not in ("bt709", "unknown", None, ""):
        return [f"zscale=pin={prim}:p=bt709:tin=bt709:t=bt709:m=bt709:r=tv", "format=yuv420p"]
    return []


def need(tool: str) -> None:
    if not shutil.which(tool):
        raise SystemExit(f"Required tool not found: {tool}")


def open_image(path: Path):
    """Open a still with EXIF orientation applied; HEIC via pillow-heif. Returns (PIL.Image, icc_bytes|None)."""
    from PIL import Image, ImageOps

    if path.suffix.lower() in {".heic", ".heif"}:
        import pillow_heif

        pillow_heif.register_heif_opener()
    img = Image.open(path)
    icc = img.info.get("icc_profile")
    img = ImageOps.exif_transpose(img)
    return img, icc


def to_srgb(img, icc: bytes | None):
    """Convert an image with an embedded profile (e.g. iPhone Display P3) to sRGB/Rec.709 primaries."""
    from io import BytesIO

    from PIL import ImageCms

    img = img.convert("RGB")
    if not icc:
        return img, "assumed sRGB (no ICC profile)"
    try:
        src = ImageCms.ImageCmsProfile(BytesIO(icc))
        desc = ImageCms.getProfileDescription(src).strip()
        if "srgb" in desc.lower():
            return img, desc
        out = ImageCms.profileToProfile(img, src, ImageCms.createProfile("sRGB"), renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="RGB")
        return out, f"{desc} -> sRGB"
    except Exception as exc:  # corrupt/unsupported profile: keep pixels, record it
        return img, f"ICC conversion failed ({exc}); pixels kept"
