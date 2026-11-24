# Posting notes (do not publish on Amr's behalf — these are for Amr)

| | Instagram | TikTok |
|---|---|---|
| File | `output/privilee_final.mp4`: **the single post** (one export for both apps) | the same file |
| Opening | "MY BEST / DUBAI *life hack*" | the same |
| Caption | `copy/posting_captions.md` → **White Friday campaign** caption | the same caption, shortened if needed |
| Cover | `output/privilee_cover.jpg` (title sits in the centre band, so it survives grid crops) | Pick the same frame in the in-app cover picker |
| Brand handle | **Not verified yet.** The search didn't find an official handle. Copy it from the links in privilee.ae's footer or Privilee's app store listing before tagging. | Same |
| Location tag | None until a venue/city is confirmed for a shot that's actually used | None |
| Music | No cleared cross-platform track supplied. **Platform music still needs to be added in each app.** Don't download a TikTok Commercial Sound and reuse it on Instagram. | Add in-app. Use only a Commercial Sound if the post is promotional. |
| Disclosure | Use the Paid partnership label only if there's a real arrangement (payment, gifted access, affiliate). Describe any relationship truthfully. | Turn on **Commercial content disclosure** for promotional brand content. An unpaid post isn't automatically exempt. |

## The White Friday link (the video's "JOIN NOW" sticker isn't tappable)

**https://privilee.ae/the-white-friday-edit**. It's the clean link: the `fbclid` and Privilee's own `utm_` tags are removed. Open it once on your phone to confirm it works, because it couldn't be checked from the build environment.

- **Instagram:** put it in your bio (then "link in bio" in the caption is true), and share the Reel to your Story with a **Link sticker** pointing to it.
- **TikTok:** put it in the bio if your account has the website field; otherwise say "link in bio" only where the link really exists.
- **Caption:** you can paste the link as text, but it won't be clickable in Reels or TikTok captions.

## Outstanding verification before posting

1. **White Friday offer**: verified 23 Nov 2026, AED 1,899 for 3 months (Amr's confirmation + Privilee's official post). UAE-only, with no cross-country access. Post it while the White Friday window is open, and check the end date in the app.
2. **Qatar and Oman line**: Oman confirmed in Privilee's cross-country FAQ (23 Nov 2026). Recheck Privilee's cross-country guide and FAQ on posting day (eligibility and Qatar tier restrictions apply). The White Friday cut contains no Qatar claim, by design.
3. **Location labels**: only labels backed by recorded evidence render (`timeline.json → locationLabels`, `verified: true` + `evidence`).
4. **Narration**: audition for pronunciation of "Privilee", "UAE" and "Qatar". Confirm the ElevenLabs plan was a paid plan at generation time (see `audio/narration/*.meta.json → licence_status`).
5. **App shots**: the app moment uses Amr's own screenshots (home screen, splash, app home, Categories). Other apps are defocused, and the splash status bar (call timer, battery) is cropped off. The 'Eva Beach Club — Now on Privilee' banner was confirmed still live by Amr on 23 Nov 2026. If posting much later, re-check quickly, because it names a specific venue.
6. **Masks**: confirm the membership QR code and account details stay masked (`masks` on the gym kiosk shot).

## Posting time

No account audience data has been supplied, so there's no universal "best time" claim. Use Instagram Insights and TikTok Analytics → Followers → active hours from Amr's own account.

## What to measure (directional, not a controlled experiment)

For each post after 24 h, 72 h and 7 days: reach/views, average watch time and % watched to the end, 3-second hold (from retention curves), shares, saves, profile visits and follows, and useful questions in the comments (e.g. "which gyms?" or "does it work in Qatar?").

- **Hook A vs Hook B**: compare the first-3-seconds retention and the share rate. Post a few days apart at similar times, and treat the result as directional.
- **Main vs cutdown**: compare completion rate against total watch time.
- **Benchmark**: Amr's own last 5–10 comparable Reels/TikToks (medians, not best posts).
- Record results in a simple sheet. They feed `copy/partnership_pitch_draft.md` placeholders only when they exist.
