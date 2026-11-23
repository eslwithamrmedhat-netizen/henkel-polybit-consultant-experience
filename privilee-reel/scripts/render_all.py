#!/usr/bin/env python3
"""Render deliverables: Remotion composite -> FFmpeg loudness finish -> output/.

  python3 scripts/render_all.py                    # every render in config/renders.json + cover + SRT + stems
  python3 scripts/render_all.py instagram_main     # just one (or several) render ids
  python3 scripts/render_all.py --allow-template   # QA only: render slates into qa/template_renders/

Refuses to write a template (any shot without media) into output/. White Friday outputs are
suffixed _review while config/offer.json verified=false. Audio is finished with two-pass
EBU R128 loudnorm (target -15 LUFS, true peak <= -1.5 dBTP, 48 kHz) with video stream-copied,
and +faststart. Exact commands are logged to output/render_log.json.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import build_props
from common import CONFIG, OUTPUT, PROCESSED, QA, ROOT, load_json, run, save_json

BROWSER = os.environ.get("REMOTION_BROWSER_EXECUTABLE", "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell")
TARGET_I, TARGET_TP, TARGET_LRA = -15.0, -1.5, 11.0
LOG: list[dict] = []


def remotion(kind: str, comp: str, out: Path, props: Path, extra: list[str]) -> None:
    cmd = ["npx", "remotion", kind, "src/index.ts", comp, str(out), f"--props={props}", f"--public-dir={PROCESSED}", "--log=error"]
    if Path(BROWSER).exists():
        cmd.append(f"--browser-executable={BROWSER}")
    cmd += extra
    LOG.append({"step": f"remotion {kind} {comp}", "cmd": " ".join(cmd)})
    res = __import__("subprocess").run(cmd, cwd=ROOT, text=True, capture_output=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout[-3000:] + res.stderr[-3000:])
        raise SystemExit(f"Remotion failed for {out.name}")


def loudness_finish(src: Path, dst: Path, muted: bool) -> dict:
    base = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-c:v", "copy"]
    if muted:
        cmd = base + ["-an", "-movflags", "+faststart", str(dst)]
        run(cmd)
        LOG.append({"step": f"finish {dst.name}", "cmd": " ".join(cmd)})
        return {"audio": "none"}
    probe = run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json", "-f", "null", "-"], check=False)
    txt = probe.stderr
    m = json.loads(txt[txt.rfind("{"): txt.rfind("}") + 1]) if "{" in txt else {}
    inp_i = float(m.get("input_i", "-inf")) if m.get("input_i") not in (None, "-inf") else float("-inf")
    if inp_i < -60:  # silence (e.g. no narration/music yet): don't amplify noise floor
        af = "aresample=48000"
        note = "audio near-silent; left unnormalised"
    else:
        af = (f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
        note = f"two-pass loudnorm from {m['input_i']} LUFS / {m['input_tp']} dBTP"
    cmd = base + ["-map", "0:a:0", "-af", af, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(dst)]
    run(cmd)
    LOG.append({"step": f"finish {dst.name}", "cmd": " ".join(cmd)})
    return {"audio": note}


def out_name(rid: str, r: dict) -> str:
    name = r["out"]
    if r["variant"] == "white_friday" and not load_json(CONFIG / "offer.json").get("verified"):
        name = name.replace(".mp4", "_review.mp4")
    return name


def render_one(rid: str, r: dict, dest_dir: Path, allow_template: bool) -> dict | None:
    props = build_props.build(rid)
    if props["isTemplate"] and not allow_template:
        missing = [s["id"] for s in props["shots"] if s["src"] is None and s["kind"] != "coverage"]
        print(f"SKIP {rid}: {len(missing)} shots still have no media ({', '.join(missing[:6])}{'…' if len(missing) > 6 else ''})")
        return None
    pfile = PROCESSED / "props" / f"{rid}.json"
    dest = dest_dir / out_name(rid, r)
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.mp4"
        extra = ["--codec=h264", "--crf=18", "--pixel-format=yuv420p", "--color-space=bt709", "--audio-codec=aac", "--audio-bitrate=320k"]
        if r.get("muted"):
            extra.append("--muted")
        remotion("render", "Film", raw, pfile, extra)
        info = loudness_finish(raw, dest, bool(r.get("muted")))
    print(f"OK   {dest.relative_to(ROOT)}  ({dest.stat().st_size / 1e6:.1f} MB)  {info['audio']}")
    return {"render": rid, "file": str(dest.relative_to(ROOT)), "variant": r["variant"], "platform": r["platform"], **info, "note": r.get("note")}


def stems(dest_dir: Path) -> list[str]:
    """Separate VO / ambience / music stems for the main film, aligned to picture (WAV 48 kHz)."""
    base = load_json(PROCESSED / "props" / "instagram_main.json")
    if not base:
        return []
    made = []
    layers = {
        "vo": {"voiceover": base["voiceover"], "music": None, "ambience": False},
        "ambience": {"voiceover": None, "music": None, "ambience": True},
        "music": {"voiceover": None, "music": base["music"], "ambience": False},
    }
    for name, over in layers.items():
        if name == "vo" and not base["voiceover"] or name == "music" and not base["music"]:
            continue
        p = {**base, **over, "captions": [], "overlays": [], "renderId": f"stem_{name}"}
        pf = PROCESSED / "props" / f"stem_{name}.json"
        save_json(pf, p)
        out = dest_dir / "stems" / f"privilee_main_stem_{name}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        remotion("render", "Film", out, pf, ["--codec=wav"])
        made.append(str(out.relative_to(ROOT)))
    return made


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_template = "--allow-template" in sys.argv
    spec = load_json(CONFIG / "renders.json")
    dest_dir = QA / "template_renders" if allow_template else OUTPUT
    dest_dir.mkdir(parents=True, exist_ok=True)
    ids = args or list(spec["renders"])
    results = [x for rid in ids if (x := render_one(rid, spec["renders"][rid], dest_dir, allow_template))]

    if not args:
        cover = build_props.build_cover()
        if not cover["isTemplate"] or allow_template:
            out = dest_dir / spec["cover"]["out"]
            remotion("still", "Cover", out, PROCESSED / "props" / "cover.json", ["--image-format=jpeg", "--jpeg-quality=92"])
            results.append({"render": "cover", "file": str(out.relative_to(ROOT))})
        sub = spec.get("subtitles") or {}
        main_props = load_json(PROCESSED / "props" / f"{sub.get('render', 'instagram_main')}.json")
        vo_id = build_props.variant(build_props.load_timeline(), main_props["variant"]).get("voiceover") if main_props else None
        if main_props and main_props.get("voiceover") and (PROCESSED / "captions" / f"{vo_id}.json").exists():
            import captions

            cap = load_json(PROCESSED / "captions" / f"{vo_id}.json")
            captions.write_srt(cap["phrases"], dest_dir / sub["out"], main_props["voiceover"]["startFrame"] / 30)
            results.append({"render": "subtitles", "file": str((dest_dir / sub["out"]).relative_to(ROOT))})
        else:
            print("No SRT: no narration integrated yet (subtitle timing is never invented).")
        if not allow_template:
            for s in stems(dest_dir):
                results.append({"render": "stem", "file": s})

    save_json(dest_dir / "render_log.json", {"rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "results": results, "commands": LOG})
    print(f"\nLog: {(dest_dir / 'render_log.json').relative_to(ROOT)} · next: python3 scripts/verify.py")


if __name__ == "__main__":
    main()
