import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { colors, OFFER_SANS, OFFER_SCRIPT_FONTS, OFFER_THIN } from "./theme";
import { OfferProps, PlatformLayout } from "./types";

const ease = Easing.bezier(0.22, 1, 0.36, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const WHITE = "#FFFFFF";
const soft = "0 2px 18px rgba(0,0,0,0.22)";

/**
 * White Friday end card over Amr's own pool footage, typeset to match Privilee's campaign post:
 *   "The" (thin serif) · "White Friday" (script) · "Edit" (thin serif)
 *   3 MONTHS (light caps) · AED 1,899 (medium) · UAE-only qualifier · CTA.
 * Fields come from config/offer.json; the review badge shows only while verified=false.
 */
export const OfferCard: React.FC<{ offer: OfferProps; layout: PlatformLayout; durationInFrames: number }> = ({ offer, layout, durationInFrames }) => {
  const frame = useCurrentFrame();
  const step = (i: number, dy = 14) => {
    const a = interpolate(frame, [6 + i * 5, 24 + i * 5], [0, 1], { ...clamp, easing: ease });
    return { opacity: a, transform: `translateY(${(1 - a) * dy}px)` };
  };
  // script "writes on" left→right
  const write = interpolate(frame, [10, 34], [0, 100], { ...clamp, easing: ease });
  const scrim = interpolate(frame, [0, 14], [0, 1], clamp);
  // sticker pops in with a small overshoot, like an app sticker being placed
  const stickerPop = interpolate(frame, [46, 54, 60], [0.6, 1.08, 1], clamp);
  const out = interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], clamp);
  const right = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  const script = OFFER_SCRIPT_FONTS[offer.scriptFont ?? "allura"] ?? OFFER_SCRIPT_FONTS.allura;
  const [months, price] = offer.headline.split("\n");

  return (
    <AbsoluteFill style={{ opacity: out }}>
      {/* soft, airy veil like the campaign creative — keeps the footage visible */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(40,48,58,0.10) 0%, rgba(40,48,58,0.34) 30%, rgba(40,48,58,0.30) 62%, rgba(40,48,58,0.12) 100%)", opacity: scrim }} />
      {offer.showText ? (
        <div style={{ position: "absolute", left: layout.sideMargin, right: Math.max(layout.sideMargin, right), top: 420, textAlign: "center", color: WHITE, textShadow: soft }}>
          {/* lock-up */}
          <div style={{ position: "relative", height: 350 }}>
            <div style={{ ...step(0, 10), position: "absolute", left: 70, top: 0, fontFamily: OFFER_THIN, fontWeight: 300, fontSize: 150, lineHeight: 1, letterSpacing: "-0.02em" }}>The</div>
            <div style={{ position: "absolute", left: 0, right: 0, top: 96, fontFamily: script, fontSize: 168, lineHeight: 1.1, whiteSpace: "nowrap", clipPath: `inset(-20% ${100 - write}% -20% 0)` }}>White Friday</div>
            <div style={{ ...step(3, 10), position: "absolute", right: 70, top: 212, fontFamily: OFFER_THIN, fontWeight: 300, fontSize: 132, lineHeight: 1, letterSpacing: "-0.02em" }}>Edit</div>
          </div>
          <div style={{ ...step(4), marginTop: 60, fontFamily: OFFER_SANS, fontWeight: 300, fontSize: 64, letterSpacing: "0.04em" }}>{months?.toUpperCase()}</div>
          <div style={{ ...step(5), marginTop: 6, fontFamily: OFFER_SANS, fontWeight: 500, fontSize: 92, letterSpacing: "0.01em" }}>{price}</div>
          <div style={{ ...step(7), marginTop: 70, fontFamily: OFFER_SANS, fontWeight: 500, fontSize: 34, letterSpacing: "0.02em", lineHeight: 1.3 }}>
            {offer.qualifier.split("\n").map((l, i) => (
              <div key={i} style={{ whiteSpace: "nowrap", opacity: i === 0 ? 0.85 : 1, fontSize: i === 0 ? 28 : 34, letterSpacing: i === 0 ? "0.22em" : "0.01em", textTransform: i === 0 ? "uppercase" : "none" }}>
                {l}
              </div>
            ))}
          </div>
          {/* "JOIN NOW" link-sticker look (visual only — Reels/TikTok posts can't hold a tappable link) */}
          <div style={{ ...step(8, 20), marginTop: 34, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 16,
                padding: "20px 38px 20px 30px",
                borderRadius: 999,
                background: "#FFFFFF",
                color: "#1E5EFF",
                fontFamily: OFFER_SANS,
                fontWeight: 500,
                fontSize: 44,
                letterSpacing: "0.06em",
                textShadow: "none",
                boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
                transform: `rotate(-2deg) scale(${stickerPop})`,
              }}
            >
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#1E5EFF" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5" />
                <path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5" />
              </svg>
              {offer.cta.toUpperCase()}
            </div>
            {offer.url ? (
              <div style={{ marginTop: 18, fontFamily: OFFER_SANS, fontWeight: 400, fontSize: 30, letterSpacing: "0.02em", opacity: 0.92 }}>{offer.url}</div>
            ) : null}
          </div>
        </div>
      ) : null}
      {offer.reviewBadge ? (
        <div style={{ position: "absolute", left: layout.sideMargin, top: Math.max(layout.topUnsafe, 60) + 20, fontFamily: OFFER_SANS, fontSize: 24, fontWeight: 500, letterSpacing: "0.08em", color: "#fff", background: colors.review, padding: "8px 16px", borderRadius: 10 }}>
          {offer.reviewBadge}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
