"""Resolve config/timeline.json variants into concrete shot lists (shared by normalize/build_props)."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from common import CONFIG, load_json


def load_timeline() -> dict:
    return load_json(CONFIG / "timeline.json")


def load_looks() -> dict:
    return load_json(CONFIG / "looks.json")


def variant(tl: dict, name: str) -> dict:
    v = deepcopy(tl["variants"][name])
    if "extends" in v:
        base = variant(tl, v.pop("extends"))
        base.update(v)
        v = base
    return v


def resolve_shots(tl: dict, name: str) -> list[dict]:
    """Shot dicts (library entry + per-variant override) in order, each with 'id'."""
    out = []
    for item in variant(tl, name)["shots"]:
        ref = {"id": item} if isinstance(item, str) else dict(item)
        sid = ref.pop("id")
        if sid not in tl["shots"]:
            raise SystemExit(f"Variant '{name}' references unknown shot '{sid}'")
        shot = deepcopy(tl["shots"][sid])
        for k, v in ref.items():
            if isinstance(v, dict) and isinstance(shot.get(k), dict):
                shot[k] = {**shot[k], **v}
            else:
                shot[k] = v
        shot["id"] = sid
        out.append(shot)
    return out


def grade_params(shot: dict, looks: dict) -> dict:
    g = dict(shot.get("grade") or {})
    ident = looks["identity"]
    preset = {**ident, **looks["presets"].get(g.get("look", "neutral"), {})}
    for k in ident:
        if k in g:
            preset[k] = g[k]
    strength = float(g.get("strength", 1.0))
    out = {}
    for k, iv in ident.items():
        pv = preset[k]
        if isinstance(iv, list):
            out[k] = [round(i + strength * (p - i), 4) for i, p in zip(iv, pv)]
        else:
            out[k] = round(iv + strength * (pv - iv), 4)
    out["brightness"] = round(out["brightness"] + float(g.get("exposure", 0.0)), 4)
    if "temperatureShift" in g:  # quick per-shot white-balance nudge in Kelvin
        out["temperature"] = round(out["temperature"] + float(g["temperatureShift"]))
        out["tempMix"] = max(out["tempMix"], 0.3)
    return out


def job_key(shot: dict, looks: dict) -> str | None:
    if not shot.get("src"):
        return None
    sig = json.dumps({"src": shot["src"], "grade": grade_params(shot, looks)}, sort_keys=True)
    return hashlib.sha1(sig.encode()).hexdigest()[:10]


def all_variant_names(tl: dict) -> list[str]:
    return list(tl["variants"].keys())
