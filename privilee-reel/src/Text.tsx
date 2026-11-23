import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { colors, SANS, SERIF } from "./theme";
import { Caption, Overlay, PlatformLayout } from "./types";

const ease = Easing.bezier(0.22, 1, 0.36, 1);

/** One motion vocabulary: soft rise + fade in (with a touch of letter-spacing settle), quick fade out. */
const useReveal = (d: number, inF = 14, outF = 8) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, inF], [0, 1], { extrapolateRight: "clamp", easing: ease });
  const b = interpolate(frame, [d - outF, d], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { opacity: Math.min(a, b), y: (1 - a) * 22, a };
};

const Eyebrow: React.FC<{ children: React.ReactNode; color?: string; a?: number }> = ({ children, color = colors.text, a = 1 }) => (
  <div
    style={{
      fontFamily: SANS,
      fontWeight: 700,
      fontSize: 36,
      letterSpacing: `${0.38 - 0.08 * a}em`,
      textShadow: colors.softShadow,
      textTransform: "uppercase",
      color,
      marginBottom: 18,
    }}
  >
    {children}
  </div>
);

const Rule: React.FC<{ color?: string }> = ({ color = colors.text }) => (
  <div style={{ width: 56, height: 2, background: color, opacity: 0.85, margin: "26px auto 0" }} />
);

export const OverlayText: React.FC<{ o: Overlay; layout: PlatformLayout; onLightCard: boolean }> = ({ o, layout, onLightCard }) => {
  const { opacity, y, a } = useReveal(o.durationInFrames);
  const right = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  const ink = onLightCard ? colors.ink : colors.text;
  const box: React.CSSProperties = {
    position: "absolute",
    left: layout.sideMargin,
    right: Math.max(layout.sideMargin, right),
    textAlign: "center",
    color: ink,
    textShadow: onLightCard ? "none" : colors.shadow,
    opacity,
    transform: `translateY(${y}px)`,
  };
  const lines = o.text.split("\n");

  if (o.type === "hook") {
    // "My best" eyebrow + serif italic statement; or two serif lines for a two-sentence hook
    const twoSentences = lines.length === 2 && /\.$/.test(lines[0]);
    if (twoSentences) {
      return (
        <div style={{ ...box, top: layout.hookCenterY - 120, fontFamily: SERIF, fontSize: 92, lineHeight: 1.02 }}>
          <div style={{ fontWeight: 500 }}>{lines[0]}</div>
          <div style={{ fontStyle: "italic", fontWeight: 400 }}>{lines[1]}</div>
        </div>
      );
    }
    return (
      <div style={{ ...box, top: layout.hookCenterY - 110 }}>
        <Eyebrow a={a}>{lines[0]}</Eyebrow>
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 400, fontSize: 104, lineHeight: 1.0, letterSpacing: "-0.01em" }}>{lines.slice(1).join(" ")}</div>
      </div>
    );
  }
  if (o.type === "title") {
    return (
      <div style={{ ...box, top: layout.titleCenterY - 120, fontFamily: SERIF, fontSize: 90, lineHeight: 1.04 }}>
        <div style={{ fontWeight: 500 }}>{lines[0]}</div>
        {lines[1] ? <div style={{ fontStyle: "italic", fontWeight: 400 }}>{lines[1]}</div> : null}
        <Rule color={ink} />
      </div>
    );
  }
  if (o.type === "coverage") {
    return (
      <div style={{ ...box, top: 780 }}>
        <Eyebrow a={a} color={ink}>
          {lines[0]}
        </Eyebrow>
        <div style={{ fontFamily: SERIF, fontWeight: 500, fontSize: 96, lineHeight: 1.02 }}>{lines.slice(1).join(" ").replace(/ and /, " & ")}</div>
      </div>
    );
  }
  if (o.type === "line") {
    // text-led review lines sit where captions will go once narration exists
    return (
      <div style={{ ...box, top: layout.captionCenterY - 70, height: 140, display: "flex", alignItems: "center", justifyContent: "center", textShadow: colors.softShadow }}>
        <span style={{ fontFamily: SANS, fontSize: 48, fontWeight: 600, lineHeight: 1.22, letterSpacing: "-0.005em" }}>{o.text}</span>
      </div>
    );
  }
  // label / brand: small, quiet, tracked, top-left inside the safe area
  return (
    <div style={{ ...box, left: layout.sideMargin, right: undefined, top: layout.labelY, textAlign: "left" }}>
      <Eyebrow a={a}>{o.text}</Eyebrow>
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
          textAlign: "center",
          fontFamily: SANS,
          fontWeight: 600,
          fontSize: 48,
          lineHeight: 1.22,
          color: colors.text,
          textShadow: colors.softShadow,
        }}
      >
        {c.text}
      </div>
    </AbsoluteFill>
  );
};

/** Gentle top/bottom gradients so white type stays legible on bright pools and skies (only when text is on). */
export const TextScrim: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background:
        "linear-gradient(180deg, rgba(0,0,0,0.30) 0%, rgba(0,0,0,0.10) 22%, rgba(0,0,0,0) 34%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.16) 64%, rgba(0,0,0,0.30) 76%, rgba(0,0,0,0.12) 90%, rgba(0,0,0,0) 100%)",
    }}
  />
);

export const Guides: React.FC<{ layout: PlatformLayout }> = ({ layout }) => {
  const red = "rgba(255,40,40,0.28)";
  const r = layout.rightRail;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: layout.topUnsafe, background: red }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: layout.bottomUnsafe, background: red }} />
      <div style={{ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h, background: red }} />
      <div style={{ position: "absolute", left: 24, bottom: 24, fontFamily: SANS, fontSize: 26, color: "#fff" }}>{layout.label} · approximate guide</div>
    </AbsoluteFill>
  );
};
