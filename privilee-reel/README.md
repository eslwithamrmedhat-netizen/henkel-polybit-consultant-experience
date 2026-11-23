# Privilee — *Different cities. Same routine.*

Editable vertical-film project for Amr's personal Privilee reel. The brief is in [`CLAUDE_CODE_PRIVILEE_REEL_PROMPT.md`](CLAUDE_CODE_PRIVILEE_REEL_PROMPT.md).
Stack: **FFmpeg/ffprobe** for audit, HDR→SDR, grading, loudness and verification; **Remotion 4.0.546 (React)** for the edit, typography, captions and audio mix.

## Status (23 Nov 2026)

| Item | State |
|---|---|
| Project, edit template, grading, captions, offer card, render and QA pipeline | ✅ built. Self-test passes end to end on synthetic media. |
| Source photos and videos | ⛔ **not received**. The iCloud link couldn't be downloaded here (see below). |
| AI narration (ElevenLabs) | ⛔ waiting for an API credential on the environment. Scripts are ready. |
| Music | ⛔ no cleared cross-platform track. Exports will need music added in each app. |
| White Friday offer | ⚠️ unverified, with a **price conflict** (artwork AED 1,899 vs third-party reports of AED 1,599 this week). Renders as `*_review.mp4` with a REVIEW badge. |

Nothing is in `output/` yet. A template with empty shots is refused there on purpose.

## Folders

```text
media/        originals (never modified; gitignored)
audio/        narration takes + metadata, cleared music/sfx (gitignored)
brand/        approved brand assets / offer artwork (gitignored)
processed/    graded intermediates, selected narration, props; fonts/ is committed (Inter, OFL)
src/          Remotion compositions (Film, Cover)
config/       timeline (edit decision list), looks, platforms, offer, voiceover, renders, asset manifest
scripts/      pipeline (Python 3 stdlib + Pillow + pillow-heif)
copy/         captions, posting notes, partnership pitch draft
qa/           contact sheets, grade before/after, frame sheets, verification report
output/       final deliverables
```

## Setup

```bash
cd privilee-reel
npm install                     # pinned Remotion 4.0.546, React 18.3.1
python3 -m pip install -r requirements.txt
export REMOTION_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell  # this cloud env; omit locally
python3 scripts/selftest.py     # optional: proves the whole chain on synthetic media (~6 min)
```

## Getting the media in

The shared iCloud link is a JavaScript page. Its photo list comes from a per-album iCloud server whose hostname changes between loads (`p119-…`, `p120-…`), and this environment can only allow exact hostnames. Any one of these works:

1. **Upload the photos and videos directly** into the Claude session (simplest).
2. **ZIP:** in Files on iPhone, long-press the folder → *Compress*, share the ZIP. Then run `python3 scripts/import_media.py /path/to/file.zip`.
3. **Folder already downloaded on a computer:** `python3 scripts/import_media.py /path/to/folder`.
4. **Allow wildcards:** add `*.icloud.com` and `*.icloud-content.com` under the environment's Network access → Allowed domains, then retry the link in a browser.

Originals are copied byte for byte. Checksums and decode status go to `config/import_manifest.private.json` (gitignored; never contains share links).

## Workflow

```bash
# 1 · audit: technical manifest + contact sheets + thumbnails
python3 scripts/import_media.py
python3 scripts/audit_media.py                       # -> config/asset_manifest.json, qa/contact_sheets/, qa/thumbnails/
python3 scripts/audit_media.py --frame clip.MOV 3.2  # native-resolution frame for close inspection
#    then fill the editorial fields in asset_manifest.json (description, role, best in/out, location + evidence, issues)

# 2 · edit: set src / in / dur / crop / grade per shot in config/timeline.json (shot library + variants)

# 3 · grade: pass 1 correction (rotation, HDR tone-map, P3→sRGB, 30 fps CFR) + pass 2 look
python3 scripts/normalize.py                         # -> processed/media/, qa/grade/_overview.jpg (inspect it!)

# 4 · narration (ElevenLabs; key comes from env or the session proxy, never printed)
python3 scripts/voiceover.py account                 # plan tier -> commercial-use status
python3 scripts/voiceover.py models
python3 scripts/voiceover.py voices male narrative
python3 scripts/voiceover.py generate audition --voice <ID> --model <ID> --take a1   # 1–2 auditions only
python3 scripts/voiceover.py generate vo_main --voice <ID> --model <ID> --take t1
python3 scripts/voiceover.py generate vo_cutdown --voice <ID> --model <ID> --take t1
python3 scripts/voiceover.py generate vo_white_friday --voice <ID> --model <ID> --take t1
python3 scripts/voiceover.py select vo_main t1   # (repeat for each script)
python3 scripts/captions.py vo_main              # phrases from the real alignment (repeat per script)

# 5 · render + verify
python3 scripts/render_all.py                    # all deliverables, cover, SRT, stems
python3 scripts/verify.py                        # -> qa/verification.md, qa/frames/*.jpg
npm run studio                                   # optional: interactive preview/edit of the composition
```

`output/render_log.json` records every exact Remotion and FFmpeg command used.

## Editing guide

- **Shots** (`config/timeline.json → shots`): `src` (relative to media/), `kind` video|image|coverage|offer, `in`, `dur` (cut-to-cut seconds), `crop {x,y,zoom}`, `move {from,to}` (stills: keep it a few %), `layout` cover|framed (framed = intentional layout for landscape material, never stretched), `speed` (<1 only for real high-frame-rate footage), `clipVolume` (ambience), `transitionIn`/`fadeOut` (seconds), `masks` (privacy rectangles in 0–1 frame coordinates for QR codes or account details), `grade {look, strength, exposure, temperatureShift, …}`.
- **Variants**: `main` (Hook A), `hook_b`, `cutdown`, `white_friday` (UAE only: no Qatar line or insert; offer card at the end). Each lists shot ids with optional per-variant overrides.
- **Overlays**: anchored to absolute times, a shot (`shot`/`endShot`) or a spoken word (`anchorWord`).
- **Location labels**: `locationLabels` entries render **only** with `verified: true` plus an `evidence` note. A filename alone isn't evidence.
- **Looks** (`config/looks.json`): gentle presets (work_city, gym_indoor, pool_beach, golden_portrait). Judge on `qa/grade/` sheets.
- **Platform layouts** (`config/platforms.json`): *approximate* guides for keeping text clear of app overlays. Render a guide preview with `python3 scripts/build_props.py instagram_main --guides` + `npx remotion still … --props=processed/props/instagram_main_guides.json`, and confirm with an in-app draft.
- **Offer** (`config/offer.json`): editable card text. Set `verified: true` only with a dated official source; the `_review` suffix and badge then disappear.
- **Music** (`config/renders.json → music`): mixed only when both `file` and a `licence` note covering Instagram **and** TikTok are set. Ducks automatically under speech.

## Deliverables (rendered by `render_all.py`)

`privilee_main.mp4`, `privilee_hook_b.mp4`, `privilee_cutdown.mp4`, `privilee_white_friday.mp4`: one **unified export each for Instagram Reels, TikTok and YouTube Shorts**, with text kept clear of the stricter of each app's approximate overlays. Also `privilee_clean_master.mp4` (narration + ambience; no music, captions or titles), `privilee_clean_picture.mp4` (silent, no text), `privilee_cover.jpg`, `privilee_subtitles.srt` (from the real narration only) and `stems/privilee_main_stem_{vo,ambience,music}.wav`. While narration is missing, the narrated edits get a `_textled_review` suffix, and White Friday stays `_review` until the offer is verified.

Spec: 1080×1920, H.264 High yuv420p, 30 fps CFR, CRF 18, Rec.709 tags, AAC 48 kHz, two-pass loudnorm to −15 LUFS / ≤ −1.5 dBTP, faststart.

## Licences

Inter font: SIL OFL (`processed/fonts/LICENSE-Inter.txt`). Remotion is free for individuals and companies of up to 3 people; larger companies need a Remotion company licence. ElevenLabs output is commercially usable only from a paid plan (recorded per take in `audio/narration/*.meta.json`).
