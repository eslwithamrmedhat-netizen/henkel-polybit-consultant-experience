# Posting notes (do not publish on Amr's behalf — these are for Amr)

| | Instagram | TikTok |
|---|---|---|
| File | `output/privilee_main.mp4` (one unified export) | the same file |
| Opening | Hook A "MY BEST DUBAI LIFE HACK" | Hook A |
| Test variant | `output/privilee_hook_b.mp4` | the same file |
| Short cut | `output/privilee_cutdown.mp4` | the same file |
| Caption | `copy/posting_captions.md` → Instagram | `copy/posting_captions.md` → TikTok |
| Cover | `output/privilee_cover.jpg` (title sits in the centre band, so it survives grid crops) | Pick the same frame in the in-app cover picker |
| Brand handle | **Not verified yet.** The search didn't find an official handle. Copy it from the links in privilee.ae's footer or Privilee's app store listing before tagging. | Same |
| Location tag | None until a venue/city is confirmed for a shot that's actually used | None |
| Music | No cleared cross-platform track supplied. **Platform music still needs to be added in each app.** Don't download a TikTok Commercial Sound and reuse it on Instagram. | Add in-app. Use only a Commercial Sound if the post is promotional. |
| Disclosure | Use the Paid partnership label only if there's a real arrangement (payment, gifted access, affiliate). Describe any relationship truthfully. | Turn on **Commercial content disclosure** for promotional brand content. An unpaid post isn't automatically exempt. |

## Outstanding verification before posting

1. **White Friday offer**: price conflict (AED 1,899 on the artwork vs AED 1,599 in third-party reports for this week). The review exports stay `_review` until `config/offer.json` → `verified: true` with a dated official source.
2. **Qatar and Oman line**: Oman confirmed in Privilee's cross-country FAQ (23 Nov 2026). Recheck Privilee's cross-country guide and FAQ on posting day (eligibility and Qatar tier restrictions apply). The White Friday cut contains no Qatar claim, by design.
3. **Location labels**: only labels backed by recorded evidence render (`timeline.json → locationLabels`, `verified: true` + `evidence`).
4. **Narration**: audition for pronunciation of "Privilee", "UAE" and "Qatar". Confirm the ElevenLabs plan was a paid plan at generation time (see `audio/narration/*.meta.json → licence_status`).
5. **App shots**: confirm the membership QR code and account details are masked (`masks` on the shot).

## Posting time

No account audience data has been supplied, so there's no universal "best time" claim. Use Instagram Insights and TikTok Analytics → Followers → active hours from Amr's own account.

## What to measure (directional, not a controlled experiment)

For each post after 24 h, 72 h and 7 days: reach/views, average watch time and % watched to the end, 3-second hold (from retention curves), shares, saves, profile visits and follows, and useful questions in the comments (e.g. "which gyms?" or "does it work in Qatar?").

- **Hook A vs Hook B**: compare the first-3-seconds retention and the share rate. Post a few days apart at similar times, and treat the result as directional.
- **Main vs cutdown**: compare completion rate against total watch time.
- **Benchmark**: Amr's own last 5–10 comparable Reels/TikToks (medians, not best posts).
- Record results in a simple sheet. They feed `copy/partnership_pitch_draft.md` placeholders only when they exist.
