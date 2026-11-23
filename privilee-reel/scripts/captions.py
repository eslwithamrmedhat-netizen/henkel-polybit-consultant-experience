#!/usr/bin/env python3
"""Captions from the ACTUAL generated narration (ElevenLabs character alignment).

  python3 scripts/captions.py <script_id>                       # -> processed/captions/<id>.json
  python3 scripts/captions.py <script_id> --srt OUT --offset S  # also write an SRT shifted by S seconds

Phrases are short readable chunks (≤ 6 words, broken at sentence ends and natural commas),
never single bouncing words. No timing is invented: with no alignment file, this exits.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import PROCESSED, load_json, save_json

MAX_WORDS = 7


def words_from_alignment(al: dict) -> list[dict]:
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, cs, ce = [], "", None, None
    for c, s, e in zip(chars, st, en):
        if c.isspace():
            if cur:
                words.append({"text": cur, "start": cs, "end": ce})
                cur = ""
            continue
        if not cur:
            cs = s
        cur += c
        ce = e
    if cur:
        words.append({"text": cur, "start": cs, "end": ce})
    return words


WEAK_END = {"the", "a", "an", "my", "your", "to", "of", "and", "or", "by", "at", "in", "on", "for", "with", "around", "across", "that", "is", "has"}
BREAK_BEFORE = {"and", "but", "since", "then", "because", "while", "by", "or", "when", "so"}


def split_clause(ws: list[dict]) -> list[list[dict]]:
    """Split a long clause at the most natural point near its middle (recursively)."""
    n = len(ws)
    if n <= MAX_WORDS:
        return [ws]
    best, best_score = n // 2, 1e9
    for i in range(2, n - 1):  # never leave a 1-word fragment
        prev = re.sub(r"\W", "", ws[i - 1]["text"]).lower()
        nxt = re.sub(r"\W", "", ws[i]["text"]).lower()
        score = abs(i - n / 2) + (2.0 if prev in WEAK_END else 0) - (2.5 if nxt in BREAK_BEFORE else 0)
        if score < best_score:
            best, best_score = i, score
    return split_clause(ws[:best]) + split_clause(ws[best:])


def phrases_from_words(words: list[dict]) -> list[dict]:
    clauses, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 0
        if re.search(r"[.!?:,;]$", w["text"]) or gap > 0.45:
            clauses.append(cur)
            cur = []
    if cur:
        clauses.append(cur)
    out = []
    for cl in clauses:
        for chunk in split_clause(cl):
            out.append({"text": " ".join(w["text"] for w in chunk), "start": round(chunk[0]["start"], 3), "end": round(chunk[-1]["end"], 3)})
    # merge a very short trailing clause into the previous one when both fit on screen
    merged: list[dict] = []
    for ph in out:
        if merged and len(ph["text"].split()) <= 2 and len(merged[-1]["text"].split()) + len(ph["text"].split()) <= MAX_WORDS and not re.search(r"[.!?:]$", merged[-1]["text"]):
            merged[-1] = {"text": merged[-1]["text"] + " " + ph["text"], "start": merged[-1]["start"], "end": ph["end"]}
        else:
            merged.append(ph)
    out = merged
    # keep each caption on screen until shortly before the next, but not across long pauses
    for a, b in zip(out, out[1:]):
        a["end"] = round(min(b["start"] - 0.05, a["end"] + 0.6), 3)
    if out:
        out[-1]["end"] = round(out[-1]["end"] + 0.6, 3)
    return out


def srt_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(int(round(t * 1000)), 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(phrases: list[dict], path: Path, offset: float) -> None:
    lines = []
    for i, p in enumerate(phrases, 1):
        lines += [str(i), f"{srt_time(p['start'] + offset)} --> {srt_time(p['end'] + offset)}", p["text"], ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build(script_id: str) -> dict:
    al_file = PROCESSED / "alignment" / f"{script_id}.json"
    data = load_json(al_file)
    if not data or not data.get("alignment"):
        raise SystemExit(f"No alignment for '{script_id}' ({al_file}). Generate + select narration first; captions are never timed by guesswork.")
    words = words_from_alignment(data["alignment"])
    phrases = phrases_from_words(words)
    cap = {"script": script_id, "words": words, "phrases": phrases, "duration": round(words[-1]["end"], 3) if words else 0}
    save_json(PROCESSED / "captions" / f"{script_id}.json", cap)
    return cap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script")
    p.add_argument("--srt")
    p.add_argument("--offset", type=float, default=0.0)
    a = p.parse_args()
    cap = build(a.script)
    print(f"{len(cap['words'])} words, {len(cap['phrases'])} caption phrases, narration {cap['duration']:.2f}s")
    for ph in cap["phrases"]:
        print(f"  {ph['start']:6.2f}–{ph['end']:6.2f}  {ph['text']}")
    if a.srt:
        write_srt(cap["phrases"], Path(a.srt), a.offset)
        print(f"SRT -> {a.srt}")


if __name__ == "__main__":
    main()
