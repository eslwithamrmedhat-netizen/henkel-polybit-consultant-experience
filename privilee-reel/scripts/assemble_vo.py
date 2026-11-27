#!/usr/bin/env python3
"""Assemble Amr's recorded takes into one film-timed narration track + captions.

  python3 scripts/assemble_vo.py

Reads config/vo_takes.json and audio/narration/amr_raw/{take_*.m4a, transcripts.json}
(Whisper word timings, made locally). Writes processed/audio/<script_id>.wav (48 kHz mono,
gently cleaned: high-pass, light denoise, soft compression) aligned to film time 0, and
processed/captions/<script_id>.json whose phrase times are absolute film seconds
(the variant's voStart must be 0).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import captions as C
from common import AUDIO, CONFIG, PROCESSED, load_json, run, save_json

RAW = AUDIO / "narration" / "amr_raw"


def main() -> None:
    cfg = load_json(CONFIG / "vo_takes.json")
    tr = load_json(RAW / "transcripts.json")
    out_wav = PROCESSED / "audio" / f"{cfg['script_id']}.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    words_all = []
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for i, seg in enumerate(cfg["segments"]):
            part = Path(td) / f"{i}.wav"
            dur = seg["out"] - seg["in"]
            af = f"atrim=start={seg['in']}:end={seg['out']},asetpts=PTS-STARTPTS,pan=mono|c0=0.5*c0+0.5*c1,aresample=48000,{cfg['processing']},afade=t=in:d=0.015,afade=t=out:st={max(0, dur - 0.04):.3f}:d=0.04"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(RAW / seg["take"]), "-af", af, str(part)])
            parts.append((part, seg["cue"]))
            # caption words: spoken text, timed from Whisper words inside the trim window
            ww = [w for w in tr[seg["take"]]["words"] if w["start"] >= seg["in"] - 0.05 and w["end"] <= seg["out"] + 0.2]
            cw = seg["text"].split()
            for j, t in enumerate(cw):
                k = round(j * (len(ww) - 1) / max(1, len(cw) - 1)) if ww else 0
                src = ww[k] if ww else {"start": seg["in"] + dur * j / len(cw), "end": seg["in"] + dur * (j + 1) / len(cw)}
                words_all.append({"text": t, "start": round(seg["cue"] + src["start"] - seg["in"], 3), "end": round(seg["cue"] + src["end"] - seg["in"], 3)})
        inputs, delays = [], []
        for i, (part, cue) in enumerate(parts):
            inputs += ["-i", str(part)]
            ms = int(round(cue * 1000))
            delays.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
        mix = ";".join(delays) + ";" + "".join(f"[d{i}]" for i in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0[a]"
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", mix, "-map", "[a]", "-ac", "1", "-ar", "48000", str(out_wav)])
    # keep words monotonic (segments never overlap)
    for a, b in zip(words_all, words_all[1:]):
        if b["start"] < a["end"]:
            a["end"] = max(a["start"] + 0.05, b["start"] - 0.01)
    phrases = []
    seg_bounds = [(s["cue"], s["cue"] + s["out"] - s["in"]) for s in cfg["segments"]]
    for a, b in seg_bounds:  # phrase per segment so captions never bridge two takes
        ws = [w for w in words_all if a - 0.01 <= w["start"] <= b + 0.01]
        phrases += C.phrases_from_words(ws)
    save_json(PROCESSED / "captions" / f"{cfg['script_id']}.json", {"script": cfg["script_id"], "words": words_all, "phrases": phrases, "duration": seg_bounds[-1][1], "source": "Amr's recorded takes"})
    print(f"VO -> {out_wav.relative_to(PROCESSED.parent)} · {len(phrases)} caption phrases")
    for p in phrases:
        print(f"  {p['start']:6.2f}–{p['end']:6.2f}  {p['text']}")


if __name__ == "__main__":
    main()
