#!/usr/bin/env python3
"""Resolve one render (config/renders.json) into the input props Remotion renders.

  python3 scripts/build_props.py <render_id> [--guides]   # -> processed/props/<render_id>.json
  python3 scripts/build_props.py --cover                  # -> processed/props/cover.json

Everything editable lives in config/; this only computes frames, picks processed files,
attaches captions from the real narration alignment and enforces the content rules
(verified-only location labels; offer review badge until verified).
"""
from __future__ import annotations

import argparse
import sys

from common import CONFIG, PROCESSED, load_json, save_json
from timeline import job_key, load_looks, load_timeline, resolve_shots, variant

FPS = 30


def f(sec: float) -> int:
    return int(round(sec * FPS))


def music_layer(spec: dict) -> dict | None:
    m = spec.get("music") or {}
    if not m.get("file"):
        return None
    if not m.get("licence"):
        print("WARNING: music.file set without a documented licence — music NOT mixed.", file=sys.stderr)
        return None
    return {"src": m["file"], "volume": m["volume"], "duckTo": m["duckTo"], "fadeIn": f(m["fadeIn"]), "fadeOut": f(m["fadeOut"])}


def shot_props(shot: dict, mm: dict, looks: dict, start: int, cut_frames: int) -> dict:
    key = job_key(shot, looks)
    entry = mm.get(key) if key else None
    p = {
        "id": shot["id"],
        "beat": shot.get("beat", ""),
        "kind": shot.get("kind", "video"),
        "from": start,
        "durationInFrames": cut_frames,
        "src": entry["file"] if entry else None,
        "mediaWidth": entry["width"] if entry else None,
        "mediaHeight": entry["height"] if entry else None,
        "crop": {"x": 0.5, "y": 0.5, "zoom": 1.0, **(shot.get("crop") or {})},
        "move": shot.get("move") or None,
        "layout": shot.get("layout", "cover"),
        "clipVolume": float(shot.get("clipVolume", 0.0)),
        "playbackRate": float(shot.get("speed", 1.0)),
        "transitionIn": f(shot.get("transitionIn", 0)),
        "fadeOut": f(shot.get("fadeOut", 0)),
        "masks": shot.get("masks") or [],
        "hasAudio": bool(entry and entry.get("hasAudio")),
    }
    if p["kind"] == "phone":
        from pathlib import Path as _P

        from PIL import Image

        ui = lambda src: f"brand/ui/{_P(src).stem}.png"
        size = lambda rel: list(Image.open(PROCESSED / rel).size)
        p["phone"] = {
            "home": ui(shot["home"]["src"]),
            "homeSize": size(ui(shot["home"]["src"])),
            "iconRect": shot["iconRect"],
            "icon": "brand/ui/privilee_icon.png",
            "splash": ui(shot["splash"]["src"]),
            "screens": [{"src": ui(sc["src"]), "size": size(ui(sc["src"])), "weight": sc.get("weight", 1.0), **({"scroll": sc["scroll"]} if "scroll" in sc else {}), **({"tap": sc["tap"]} if "tap" in sc else {})} for sc in shot["screens"]],
        }
        return p
    if shot.get("freeze"):
        p["kind"] = "image"
    elif entry and p["kind"] in ("video", "offer", "coverage"):
        p["trimBefore"] = max(0, f(float(shot.get("in", 0)) - entry.get("offset", 0)))
    if p["kind"] == "brand":
        from PIL import Image

        p["src"] = f"brand/{__import__('pathlib').Path(shot['src']).stem}.png"
        with Image.open(PROCESSED / p["src"]) as im:
            p["mediaWidth"], p["mediaHeight"] = im.size
        return p
    if shot.get("src") and not entry:
        raise SystemExit(f"Shot '{shot['id']}' has src but no processed intermediate — run scripts/normalize.py")
    return p


def build(render_id: str, guides: bool = False) -> dict:
    tl, looks, spec = load_timeline(), load_looks(), load_json(CONFIG / "renders.json")
    r = spec["renders"][render_id]
    v = variant(tl, r["variant"])
    platforms = load_json(CONFIG / "platforms.json")
    offer_cfg = load_json(CONFIG / "offer.json")
    mm = load_json(PROCESSED / "media_map.json", {})

    resolved = resolve_shots(tl, r["variant"])
    # variety rules: never two selfies in a row; warn when the same source sits next to itself
    for a, b in zip(resolved, resolved[1:]):
        if a.get("selfie") and b.get("selfie"):
            raise SystemExit(f"{r['variant']}: two selfies in a row ({a['id']} -> {b['id']}) — interleave other shots")
        if a.get("src") and a.get("src") == b.get("src"):
            print(f"note: {a['id']} and {b['id']} share a source back to back", file=sys.stderr)
    shots, cursor, starts, ends = [], 0, {}, {}
    for s in resolved:
        tin = f(s.get("transitionIn", 0))
        start = max(0, cursor - tin)
        dur = f(s["dur"]) + (cursor - start)
        sp = shot_props(s, mm, looks, start, dur)
        shots.append(sp)
        starts.setdefault(s["id"], start)
        ends[s["id"]] = start + dur
        cursor = start + dur
    total = cursor
    # brand cards borrow the next real shot (blurred) as a full-frame backdrop
    for i, sp in enumerate(shots):
        if sp["kind"] == "brand":
            nxt = next((x for x in shots[i + 1:] if x["src"] and x["kind"] != "brand"), None)
            sp["backdrop"] = nxt["src"] if nxt and nxt["src"].lower().endswith((".jpg", ".jpeg", ".png")) else None

    vo = None
    captions = []
    vo_id = v.get("voiceover")
    vo_start = f(v.get("voStart", 0.25))
    cap = load_json(PROCESSED / "captions" / f"{vo_id}.json") if vo_id else None
    audio_file = next((p for p in (PROCESSED / "audio").glob(f"{vo_id}.*")), None) if vo_id and (PROCESSED / "audio").exists() else None
    if r.get("voiceover") and audio_file:
        vo = {"src": f"audio/{audio_file.name}", "startFrame": vo_start, "volume": 1.0}
    if r.get("captions") and cap:
        captions = [{"text": p["text"], "from": vo_start + f(p["start"]), "to": vo_start + f(p["end"])} for p in cap["phrases"]]
    speech = [[vo_start + f(p["start"]), vo_start + f(p["end"])] for p in (cap or {}).get("phrases", [])] if vo else []

    overlays = []
    if r.get("overlays"):
        for o in v.get("overlays", []):
            # text-led lines tell the story only when no narration is integrated; captions take over otherwise
            if o.get("textLed") and vo:
                continue
            if "shot" in o:
                a = starts[o["shot"]] + f(o.get("offset", 0))
                b = ends[o.get("endShot", o["shot"])] + f(o.get("endOffset", 0))
            elif "anchorWord" in o:
                w = next((w for w in (cap or {}).get("words", []) if o["anchorWord"].lower() in w["text"].lower()), None)
                if not w:
                    continue
                a = vo_start + f(w["start"])
                b = a + f(o.get("hold", 2.0))
            else:
                a, b = f(o["start"]), f(o["end"])
            overlays.append({"type": o["type"], "text": o["text"], "from": a, "durationInFrames": max(1, b - a), **({"boxed": True} if o.get("boxed") else {})})
        for lab in tl.get("locationLabels", []):
            if lab.get("verified") is True and lab.get("evidence") and lab.get("shot") in starts:
                a = starts[lab["shot"]]
                overlays.append({"type": "label", "text": lab["text"], "from": a + f(0.2), "durationInFrames": max(1, ends[lab["shot"]] - a - f(0.4))})

    offer = None
    if v.get("offer"):
        offer = {
            **offer_cfg["card"],
            "artwork": (offer_cfg.get("artwork") or {}).get("file"),
            "reviewBadge": None if offer_cfg.get("verified") else offer_cfg.get("reviewBadge"),
            "showText": r.get("overlays", True),
            "scriptFont": offer_cfg.get("scriptFont", "allura"),
            "url": offer_cfg.get("displayUrl"),
        }

    template = any(s["src"] is None and s["kind"] not in ("coverage", "phone", "brand") for s in shots)
    props = {
        "renderId": render_id,
        "variant": r["variant"],
        "fps": FPS,
        "width": tl["width"],
        "height": tl["height"],
        "durationInFrames": total,
        "platform": {"name": r["platform"], **platforms[r["platform"]]},
        "shots": shots,
        "overlays": overlays,
        "captions": captions,
        "voiceover": vo,
        "speech": speech,
        "music": music_layer(spec) if r.get("music") else None,
        "ambience": bool(r.get("ambience")),
        "offer": offer,
        "showGuides": guides,
        "isTemplate": template,
        "textLedReview": bool(r.get("voiceover")) and vo is None,
    }
    save_json(PROCESSED / "props" / f"{render_id}{'_guides' if guides else ''}.json", props)
    return props


def build_cover() -> dict:
    tl, looks, spec = load_timeline(), load_looks(), load_json(CONFIG / "renders.json")
    c = spec["cover"]
    mm = load_json(PROCESSED / "media_map.json", {})
    shot = next(s for s in resolve_shots(tl, "main") if s["id"] == c["shot"])
    shot = {**shot, "in": float(shot.get("in", 0)) + float(c.get("at", 0)), "move": None}
    sp = shot_props(shot, mm, looks, 0, 1)
    props = {"title": c["title"], "shot": sp, "width": tl["width"], "height": tl["height"], "isTemplate": sp["src"] is None}
    save_json(PROCESSED / "props" / "cover.json", props)
    return props


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("render", nargs="?")
    ap.add_argument("--guides", action="store_true")
    ap.add_argument("--cover", action="store_true")
    a = ap.parse_args()
    if a.cover:
        p = build_cover()
        print(f"cover props · template={p['isTemplate']}")
    else:
        p = build(a.render, a.guides)
        print(f"{a.render}: {p['durationInFrames']} frames ({p['durationInFrames'] / FPS:.2f}s) · {len(p['shots'])} shots · {len(p['captions'])} captions · vo={'yes' if p['voiceover'] else 'no'} · music={'yes' if p['music'] else 'no'} · template={p['isTemplate']}")
