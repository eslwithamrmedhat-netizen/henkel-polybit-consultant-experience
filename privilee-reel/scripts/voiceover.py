#!/usr/bin/env python3
"""ElevenLabs narration: inspect account/voices/models, generate takes with timestamps, select.

  python3 scripts/voiceover.py account
  python3 scripts/voiceover.py models
  python3 scripts/voiceover.py voices [search words]
  python3 scripts/voiceover.py generate <script_id> --voice VOICE_ID --model MODEL_ID [--take NAME]
  python3 scripts/voiceover.py select <script_id> <take>

Credentials: the API key is read from ELEVENLABS_API_KEY, or injected by the session's
network proxy when a credential for api.elevenlabs.io is saved on the environment. It is
never printed, logged or written to disk. Spoken text comes ONLY from config/voiceover.json
'scripts' — the direction notes are never sent for speech.

Each take keeps the service's original output (PCM wrapped as WAV, or MP3 as delivered —
never transcoded "up"), the character alignment, and a metadata file recording provider,
actual model/voice IDs, settings, date, output format and plan-based licence status.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timezone

from common import AUDIO, CONFIG, PROCESSED, load_json, save_json

API = "https://api.elevenlabs.io"
NARR = AUDIO / "narration"


def _req(method: str, path: str, body: dict | None = None, query: dict | None = None):
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    headers = {"xi-api-key": os.environ.get("ELEVENLABS_API_KEY") or "proxy-injected", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        raise RuntimeError(f"ElevenLabs {method} {path} -> HTTP {e.code}: {detail}") from None


def account() -> dict:
    sub = _req("GET", "/v1/user/subscription")
    keep = {k: sub.get(k) for k in ("tier", "status", "character_count", "character_limit", "next_character_count_reset_unix", "can_use_instant_voice_cloning")}
    keep["characters_remaining"] = (sub.get("character_limit") or 0) - (sub.get("character_count") or 0)
    keep["commercial_use"] = licence_status(sub.get("tier"))
    return keep


def licence_status(tier: str | None) -> str:
    if not tier:
        return "unknown — check plan before commercial use"
    if tier.lower() == "free":
        return "NOT commercially licensed (free plan output cannot be used commercially; upgrading later does not relicense it)"
    return f"paid plan '{tier}': commercial use permitted subject to ElevenLabs terms (excludes Beta services) — reconfirm terms at publish time"


def cmd_models(_):
    for m in _req("GET", "/v1/models"):
        if not m.get("can_do_text_to_speech"):
            continue
        langs = len(m.get("languages") or [])
        flags = [f for f in ("can_be_finetuned", "requires_alpha_access") if m.get(f)]
        print(f"{m['model_id']:32s} {m.get('name', ''):38s} langs={langs:<3d} {' '.join(flags)}")
        if m.get("description"):
            print(f"{'':32s} {m['description'][:150]}")


def cmd_voices(a):
    q = {"page_size": 100}
    if a.search:
        q["search"] = " ".join(a.search)
    try:
        res = _req("GET", "/v2/voices", query=q)
        voices = res.get("voices", [])
    except RuntimeError:
        voices = _req("GET", "/v1/voices").get("voices", [])
    for v in voices:
        labels = v.get("labels") or {}
        lab = ", ".join(f"{k}={labels[k]}" for k in ("gender", "age", "accent", "use_case", "descriptive") if labels.get(k))
        print(f"{v['voice_id']}  {v.get('name', '')[:28]:28s} [{v.get('category', '')}] {lab}")
        if v.get("sharing", {}) and v["sharing"].get("status") == "copied":
            print("    (library voice — check its own usage terms)")


def cmd_account(_):
    print(json.dumps(account(), indent=2))


def cmd_generate(a):
    cfg = load_json(CONFIG / "voiceover.json")
    script = cfg["scripts"].get(a.script)
    if not script:
        raise SystemExit(f"Unknown script id '{a.script}'. Options: {', '.join(cfg['scripts'])}")
    if script.get("gated"):
        offer = load_json(CONFIG / "offer.json")
        if not offer.get("verified"):
            raise SystemExit(f"'{a.script}' is gated: {script['gated']}")
    voice = a.voice or cfg.get("voice_id")
    model = a.model or cfg.get("model_id")
    if not voice or not model:
        raise SystemExit("Choose a voice and model first (voices/models commands), then pass --voice/--model or set them in config/voiceover.json.")
    text = script["text"]
    acct = account()
    if acct["characters_remaining"] < len(text):
        raise SystemExit(f"Not enough characters left on the plan ({acct['characters_remaining']} < {len(text)}). Not generating; no overage/upgrade attempted.")
    settings = dict(cfg.get("voice_settings") or {})
    body = {"text": text, "model_id": model, "voice_settings": settings}
    if a.seed is not None:
        body["seed"] = a.seed
    last_err = None
    for fmt in cfg.get("output_formats_preference", ["mp3_44100_128"]):
        try:
            res = _req("POST", f"/v1/text-to-speech/{voice}/with-timestamps", body=body, query={"output_format": fmt})
            break
        except RuntimeError as e:
            last_err = e
            if "output_format" in str(e) or "HTTP 403" in str(e) or "HTTP 422" in str(e) or "HTTP 400" in str(e):
                print(f"  format {fmt} not available on this account/model, trying next…", file=sys.stderr)
                if "speed" in str(e) and "speed" in settings:
                    settings.pop("speed")
                continue
            raise
    else:
        raise SystemExit(f"Generation failed: {last_err}")

    NARR.mkdir(parents=True, exist_ok=True)
    take = a.take or datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = NARR / f"{a.script}__{take}"
    raw = base64.b64decode(res["audio_base64"])
    if fmt.startswith("pcm_"):
        rate = int(fmt.split("_")[1])
        path = stem.with_suffix(".wav")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(raw)
        fmt_note = f"{fmt}: lossless 16-bit PCM from the service, wrapped in WAV (no transcoding)"
    else:
        path = stem.with_suffix(".mp3")
        path.write_bytes(raw)
        fmt_note = f"{fmt}: MP3 as delivered by the service (lossless PCM not available to this account/model)"
    save_json(stem.with_suffix(".alignment.json"), {"alignment": res.get("alignment"), "normalized_alignment": res.get("normalized_alignment")})
    voice_name = None
    try:
        voice_name = _req("GET", f"/v1/voices/{voice}").get("name")
    except RuntimeError:
        pass
    meta = {
        "provider": "ElevenLabs",
        "endpoint": "POST /v1/text-to-speech/{voice_id}/with-timestamps",
        "model_id": model,
        "voice_id": voice,
        "voice_name": voice_name,
        "voice_settings": settings,
        "seed": a.seed,
        "output_format": fmt_note,
        "script_id": a.script,
        "spoken_text": text,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_tier": acct.get("tier"),
        "licence_status": acct["commercial_use"],
        "pronunciation_check": "PENDING human audition (Privilee / UAE / Qatar / price)",
        "listen_check": "PENDING — automated pipeline cannot listen; audition before publishing",
    }
    save_json(stem.with_suffix(".meta.json"), meta)
    print(f"Saved {path.relative_to(AUDIO.parent)}  ({len(raw)} bytes)  ·  {fmt}")
    print(f"Licence: {meta['licence_status']}")


def cmd_select(a):
    cands = [p for p in NARR.glob(f"{a.script}__{a.take}.*") if p.suffix in (".wav", ".mp3")]
    if not cands:
        raise SystemExit(f"No take audio/narration/{a.script}__{a.take}.(wav|mp3)")
    src = cands[0]
    dst = PROCESSED / "audio" / f"{a.script}{src.suffix}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    for old in dst.parent.glob(f"{a.script}.*"):
        old.unlink()
    shutil.copy2(src, dst)
    (PROCESSED / "alignment").mkdir(exist_ok=True)
    shutil.copy2(src.with_suffix(".alignment.json"), PROCESSED / "alignment" / f"{a.script}.json")
    sel = load_json(NARR / "selected.json", {})
    sel[a.script] = {"take": a.take, "file": src.name}
    save_json(NARR / "selected.json", sel)
    print(f"Selected {src.name} -> {dst.relative_to(PROCESSED.parent)}. Next: python3 scripts/captions.py {a.script}")


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("account").set_defaults(fn=cmd_account)
    sp.add_parser("models").set_defaults(fn=cmd_models)
    v = sp.add_parser("voices")
    v.add_argument("search", nargs="*")
    v.set_defaults(fn=cmd_voices)
    g = sp.add_parser("generate")
    g.add_argument("script")
    g.add_argument("--voice")
    g.add_argument("--model")
    g.add_argument("--take")
    g.add_argument("--seed", type=int)
    g.set_defaults(fn=cmd_generate)
    s = sp.add_parser("select")
    s.add_argument("script")
    s.add_argument("take")
    s.set_defaults(fn=cmd_select)
    a = p.parse_args()
    try:
        a.fn(a)
    except RuntimeError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
