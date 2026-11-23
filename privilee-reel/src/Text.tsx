import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { colors, FONT } from "./theme";
import { Caption, Overlay, PlatformLayout } from "./types";

const ease = Easing.bezier(0.22, 1, 0.36, 1);

/** Gentle rise + fade in, quick fade out. One motion vocabulary for every title. */
const useReveal = (d: number, inF = 12, outF = 8) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, inF], [0, 1], { extrapolateRight: "clamp", easing: ease });
  const b = interpolate(frame, [d - outF, d], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { opacity: Math.min(a, b), y: (1 - a) * 18 };
};

const lines = (t: string) => t.split("\n").map((l, i) => <div key={i}>{l}</div>);

export const OverlayText: React.FC<{ o: Overlay; layout: PlatformLayout; onLightCard: boolean }> = ({ o, layout, onLightCard }) => {
  const { opacity, y } = useReveal(o.durationInFrames);
  const right = 1080 - layout.rightRail.x > 0 && layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  const box: React.CSSProperties = {
    position: "absolute",
    left: layout.sideMargin,
    right: Math.max(layout.sideMargin, right),
    textAlign: "center",
    fontFamily: FONT,
    color: onLightCard ? colors.ink : colors.text,
    textShadow: onLightCard ? "none" : colors.shadow,
    opacity,
    transform: `translateY(${y}px)`,
  };
  if (o.type === "hook") {
    return (
      <div style={{ ...box, top: layout.hookCenterY - 110, fontSize: 78, fontWeight: 700, letterSpacing: "0.02em", lineHeight: 1.08 }}>
        {lines(o.text)}
      </div>
    );
  }
  if (o.type === "title") {
    return (
      <div style={{ ...box, top: layout.titleCenterY - 90, fontSize: 70, fontWeight: 600, letterSpacing: "-0.01em", lineHeight: 1.1 }}>
        {lines(o.text)}
      </div>
    );
  }
  if (o.type === "coverage") {
    return (
      <div style={{ ...box, top: 860, fontSize: 60, fontWeight: 600, lineHeight: 1.15 }}>
        {onLightCard ? <div style={{ width: 64, height: 3, background: colors.ink, margin: "0 auto 34px", opacity: 0.7 }} /> : null}
        {lines(o.text)}
      </div>
    );
  }
  if (o.type === "line") {
    // text-led review lines: sit where captions will go once narration exists
    return (
      <div style={{ ...box, top: layout.captionCenterY - 70, height: 140, display: "flex", alignItems: "center", justifyContent: "center", textShadow: "none" }}>
        <span style={{ fontSize: 52, fontWeight: 600, lineHeight: 1.2, color: colors.text, background: colors.captionBg, padding: "12px 26px 14px", borderRadius: 18 }}>{o.text}</span>
      </div>
    );
  }
  // label / brand: small, quiet, top-left inside the safe area
  return (
    <div style={{ ...box, left: layout.sideMargin, right: undefined, top: layout.labelY, textAlign: "left", fontSize: 34, fontWeight: 500, letterSpacing: "0.06em" }}>
      {o.text}
    </div>
  );
};

export const CaptionText: React.FC<{ c: Caption; layout: PlatformLayout }> = ({ c, layout }) => {
  const frame = useCurrentFrame();
  const d = c.to - c.from;
  const opacity = Math.min(interpolate(frame, [0, 4], [0, 1], { extrapolateRight: "clamp" }), interpolate(frame, [d - 3, d], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const rightInset = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: layout.sideMargin,
          right: Math.max(layout.sideMargin, rightInset),
          top: layout.captionCenterY - 60,
          height: 120,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
        }}
      >
        <span
          style={{
            fontFamily: FONT,
            fontWeight: 600,
            fontSize: 48,
            lineHeight: 1.22,
            color: colors.text,
            background: colors.captionBg,
            padding: "10px 24px 12px",
            borderRadius: 18,
            textAlign: "center",
            boxDecorationBreak: "clone",
            WebkitBoxDecorationBreak: "clone",
          }}
        >
          {c.text}
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const Guides: React.FC<{ layout: PlatformLayout }> = ({ layout }) => {
  const red = "rgba(255,40,40,0.28)";
  const r = layout.rightRail;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: layout.topUnsafe, background: red }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: layout.bottomUnsafe, background: red }} />
      <div style={{ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h, background: red }} />
      <div style={{ position: "absolute", left: 24, bottom: 24, fontFamily: FONT, fontSize: 26, color: "#fff" }}>{layout.label} · approximate guide</div>
    </AbsoluteFill>
  );
};
