import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { colors, SANS, SERIF } from "./theme";
import { OfferProps, PlatformLayout } from "./types";

const ease = Easing.bezier(0.22, 1, 0.36, 1);

/**
 * White Friday end card. Sits over Amr's own pool clip (rendered underneath by <Shot/>).
 * Square artwork, if supplied, is CONTAINED — never stretched to 9:16 or cropped.
 * Text is fully editable in config/offer.json. A review badge shows until the offer is verified.
 */
export const OfferCard: React.FC<{ offer: OfferProps; layout: PlatformLayout; durationInFrames: number }> = ({ offer, layout, durationInFrames }) => {
  const frame = useCurrentFrame();
  const step = (i: number) => {
    const a = interpolate(frame, [8 + i * 5, 22 + i * 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
    return { opacity: a, transform: `translateY(${(1 - a) * 16}px)` };
  };
  const scrim = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const out = interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const right = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  const art = offer.artwork;
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(20,18,16,0.10) 0%, rgba(20,18,16,0.52) 45%, rgba(20,18,16,0.62) 100%)", opacity: scrim }} />
      {offer.showText ? (
        <div
          style={{
            position: "absolute",
            left: layout.sideMargin,
            right: Math.max(layout.sideMargin, right),
            top: art ? 330 : 560,
            textAlign: "center",
            fontFamily: SANS,
            color: colors.text,
            textShadow: colors.shadow,
          }}
        >
          {art ? (
            <>
              <div style={{ ...step(0), width: 680, margin: "0 auto", borderRadius: 18, overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,0.38)" }}>
                <Img src={staticFile(art)} style={{ width: "100%", height: "auto", display: "block" }} />
              </div>
              <div style={{ ...step(2), fontSize: 34, fontWeight: 500, marginTop: 40, opacity: 0.95 }}>{offer.qualifier}</div>
              <div style={{ ...step(3), display: "inline-block", fontSize: 42, fontWeight: 600, marginTop: 36, paddingBottom: 8, borderBottom: `2px solid ${colors.text}` }}>{offer.cta}</div>
            </>
          ) : (
            <>
              <div style={{ ...step(1), fontSize: 28, fontWeight: 600, letterSpacing: "0.34em" }}>{offer.eyebrow}</div>
              <div style={{ ...step(2), fontFamily: SERIF, fontSize: 92, fontWeight: 500, marginTop: 26, lineHeight: 1.04 }}>
                {offer.headline.split("\n").map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
              </div>
              <div style={{ ...step(3), fontSize: 34, fontWeight: 500, marginTop: 30, opacity: 0.92 }}>{offer.qualifier}</div>
              <div style={{ ...step(4), display: "inline-block", fontSize: 42, fontWeight: 600, marginTop: 64, paddingBottom: 8, borderBottom: `2px solid ${colors.text}` }}>{offer.cta}</div>
            </>
          )}
        </div>
      ) : null}
      {offer.reviewBadge ? (
        <div
          style={{
            position: "absolute",
            left: layout.sideMargin,
            top: Math.max(layout.topUnsafe, 60) + 20,
            fontFamily: SANS,
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "#fff",
            background: colors.review,
            padding: "8px 16px",
            borderRadius: 10,
          }}
        >
          {offer.reviewBadge}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
