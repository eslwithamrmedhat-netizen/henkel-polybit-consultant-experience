#!/usr/bin/env python3
"""Import supplied originals into media/ and write the PRIVATE import manifest.

Usage:
  python3 scripts/import_media.py                 # register files already placed in media/
  python3 scripts/import_media.py /path/to/folder # copy a downloaded folder (recursively)
  python3 scripts/import_media.py /path/to.zip    # extract a shared ZIP

Originals are copied byte-for-byte (never re-encoded). Name collisions get a numeric
suffix and are recorded. Each file is checked for decodability. The manifest
(config/import_manifest.private.json) is gitignored and must never contain share links
or tokens.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from common import CONFIG, MEDIA, ffprobe, load_json, media_kind, open_image, save_json, sha256, video_summary

MANIFEST = CONFIG / "import_manifest.private.json"
SKIP = {".DS_Store", "Thumbs.db", ".gitkeep"}


def decodes(path: Path, kind: str) -> tuple[bool, str]:
    if kind == "image":
        try:
            img, _ = open_image(path)
            img.load()
            return True, f"{img.width}x{img.height}"
        except Exception as exc:
            return False, f"image decode failed: {exc}"
    probe = ffprobe(path)
    if "error" in probe:
        return False, probe["error"]
    if kind == "video":
        s = video_summary(probe)
        return (s["decodable"], f"{s.get('display_size')} {s.get('duration', 0):.2f}s") if s["decodable"] else (False, "no video stream")
    return True, "audio"


def unique_dest(name: str) -> tuple[Path, str | None]:
    dest = MEDIA / name
    if not dest.exists():
        return dest, None
    stem, suf, i = dest.stem, dest.suffix, 2
    while (MEDIA / f"{stem}__{i}{suf}").exists():
        i += 1
    new = MEDIA / f"{stem}__{i}{suf}"
    return new, f"renamed from {name} to avoid a collision"


def main() -> None:
    MEDIA.mkdir(exist_ok=True)
    manifest = load_json(MANIFEST, {"files": []})
    known = {f["sha256"]: f for f in manifest["files"]}
    sources: list[Path] = []
    tmp = None
    if len(sys.argv) > 1:
        src = Path(sys.argv[1]).expanduser()
        if src.suffix.lower() == ".zip":
            tmp = tempfile.TemporaryDirectory()
            with zipfile.ZipFile(src) as z:
                for member in z.namelist():  # refuse path traversal
                    if member.startswith("/") or ".." in Path(member).parts:
                        raise SystemExit(f"Unsafe path in ZIP: {member}")
                z.extractall(tmp.name)
            src = Path(tmp.name)
        sources = [p for p in sorted(src.rglob("*")) if p.is_file() and p.name not in SKIP and "__MACOSX" not in p.parts]
    else:
        sources = [p for p in sorted(MEDIA.iterdir()) if p.is_file() and p.name not in SKIP]

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for p in sources:
        kind = media_kind(p)
        digest = sha256(p)
        if digest in known:
            print(f"= {p.name} already imported as {known[digest]['local']}")
            continue
        note = None
        if p.parent.resolve() == MEDIA.resolve():
            dest = p
        else:
            dest, note = unique_dest(p.name)
            shutil.copy2(p, dest)
        ok, detail = decodes(dest, kind) if kind else (False, "unsupported file type")
        entry = {
            "local": str(dest.relative_to(MEDIA.parent)),
            "original_name": p.name,
            "bytes": dest.stat().st_size,
            "sha256": digest,
            "kind": kind,
            "status": "available" if ok else "not decodable",
            "detail": detail,
            "imported_at": now,
        }
        if note:
            entry["note"] = note
        manifest["files"].append(entry)
        known[digest] = entry
        print(f"{'+' if ok else '!'} {entry['local']}  {kind}  {detail}")
    save_json(MANIFEST, manifest)
    ok_n = sum(f["status"] == "available" for f in manifest["files"])
    print(f"\n{ok_n}/{len(manifest['files'])} files available. Manifest: {MANIFEST.relative_to(MEDIA.parent)} (private)")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
