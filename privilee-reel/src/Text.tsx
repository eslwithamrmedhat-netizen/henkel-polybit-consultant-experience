import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { colors, DISPLAY, SANS, SCRIPT } from "./theme";
import { Caption, Overlay, PlatformLayout } from "./types";

const ease = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Shared exit: quick fade + small lift. */
const useExit = (d: number, outF = 7) => {
  const frame = useCurrentFrame();
  return {
    o: interpolate(frame, [d - outF, d], [1, 0], clamp),
    y: interpolate(frame, [d - outF, d], [0, -12], clamp),
  };
};

/** Heavy condensed capitals, revealed from behind their own baseline. */
const Display: React.FC<{ children: React.ReactNode; size: number; delay?: number; color?: string }> = ({ children, size, delay = 0, color = colors.text }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 14], [0, 1], { ...clamp, easing: ease });
  return (
    <div style={{ overflow: "hidden", paddingTop: "0.04em", paddingBottom: "0.02em" }}>
      <div
        style={{
          fontFamily: DISPLAY,
          fontSize: size,
          lineHeight: 0.9,
          letterSpacing: "0.005em",
          textTransform: "uppercase",
          color,
          textShadow: colors.shadow,
          transform: `translateY(${(1 - t) * 105}%)`,
        }}
      >
        {children}
      </div>
    </div>
  );
};

/** Elegant italic accent, drifting in a beat after the capitals. */
const Script: React.FC<{ children: React.ReactNode; size: number; delay?: number; style?: React.CSSProperties }> = ({ children, size, delay = 6, style }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 16], [0, 1], { ...clamp, easing: ease });
  return (
    <div
      style={{
        fontFamily: SCRIPT,
        fontStyle: "italic",
        fontSize: size,
        lineHeight: 0.95,
        letterSpacing: "-0.01em",
        color: colors.accent,
        textShadow: colors.softShadow,
        opacity: t,
        transform: `translateX(${(1 - t) * -26}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Tracked uppercase label that settles its letter-spacing as it appears. */
const Eyebrow: React.FC<{ children: React.ReactNode; delay?: number }> = ({ children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 18], [0, 1], { ...clamp, easing: ease });
  return (
    <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 32, letterSpacing: `${0.5 - 0.14 * t}em`, textTransform: "uppercase", color: colors.text, opacity: t, marginBottom: 10, textShadow: colors.softShadow }}>
      {children}
    </div>
  );
};

/** Supporting line: words rise in one after another. */
const Words: React.FC<{ text: string; size: number; delay?: number }> = ({ text, size, delay = 0 }) => {
  const frame = useCurrentFrame();
  return (
    <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: size, lineHeight: 1.12, letterSpacing: "-0.022em", textWrap: "balance" } as React.CSSProperties}>
      {text.split(" ").map((w, i) => {
        const t = interpolate(frame, [delay + i * 2, delay + i * 2 + 10], [0, 1], { ...clamp, easing: ease });
        return (
          <span key={i} style={{ display: "inline-block", opacity: t, transform: `translateY(${(1 - t) * 24}px)`, marginRight: "0.24em" }}>
            {w}
          </span>
        );
      })}
    </span>
  );
};

/** "Different cities. / Same routine." → DIFFERENT / CITIES. (capitals) + same routine. (script) */
const TitleLockup: React.FC<{ a: string; b?: string; size: number }> = ({ a, b, size }) => {
  const words = a.split(" ");
  return (
    <div>
      {words.map((w, i) => (
        <Display key={i} size={size} delay={i * 4}>
          {w}
        </Display>
      ))}
      {b ? (
        <Script size={size * 0.74} delay={words.length * 4 + 2} style={{ marginTop: -size * 0.12 }}>
          {b.charAt(0).toLowerCase() + b.slice(1)}
        </Script>
      ) : null}
    </div>
  );
};

export const OverlayText: React.FC<{ o: Overlay; layout: PlatformLayout; onLightCard: boolean }> = ({ o, layout }) => {
  const { o: exitO, y: exitY } = useExit(o.durationInFrames);
  const right = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  const box: React.CSSProperties = {
    position: "absolute",
    left: layout.sideMargin,
    right: Math.max(layout.sideMargin, right),
    textAlign: "center",
    opacity: exitO,
    transform: `translateY(${exitY}px)`,
  };
  const lines = o.text.split("\n");

  if (o.type === "hook") {
    if (lines.length === 2 && /\.$/.test(lines[0])) {
      return (
        <div style={{ ...box, top: layout.hookCenterY - 240 }}>
          <TitleLockup a={lines[0]} b={lines[1]} size={176} />
        </div>
      );
    }
    // "My best / Dubai life hack"  →  MY BEST · DUBAI (huge capitals) · life hack (script)
    const words = lines.slice(1).join(" ").split(" ");
    return (
      <div style={{ ...box, top: layout.hookCenterY - 230 }}>
        <Eyebrow>{lines[0]}</Eyebrow>
        <Display size={236}>{words[0]}</Display>
        <Script size={150} delay={7} style={{ marginTop: -34 }}>
          {words.slice(1).join(" ").toLowerCase()}
        </Script>
      </div>
    );
  }
  if (o.type === "title") {
    return (
      <div style={{ ...box, top: layout.titleCenterY - 290 }}>
        <TitleLockup a={lines[0]} b={lines[1]} size={168} />
      </div>
    );
  }
  if (o.type === "coverage") {
    const place = lines.slice(1).join(" ").replace(/ and /, " & ");
    const [p1, p2] = place.split(" & ");
    return (
      <div style={{ ...box, top: 700 }}>
        <Eyebrow>{lines[0]}</Eyebrow>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 22, whiteSpace: "nowrap" }}>
          <Display size={128}>{p1}</Display>
          {p2 ? (
            <>
              <Script size={112} delay={5}>
                &amp;
              </Script>
              <Display size={128} delay={8}>
                {p2}
              </Display>
            </>
          ) : null}
        </div>
      </div>
    );
  }
  if (o.type === "line") {
    return (
      <div style={{ ...box, color: colors.text, top: layout.captionCenterY - 90, height: 180, display: "flex", alignItems: "center", justifyContent: "center", textShadow: o.boxed ? "none" : colors.softShadow, textWrap: "balance" } as React.CSSProperties}>
        <span style={o.boxed ? { background: "rgba(16,22,34,0.66)", backdropFilter: "blur(14px)", padding: "16px 32px 18px", borderRadius: 28 } : {}}>
          <Words text={o.text} size={62} />
        </span>
      </div>
    );
  }
  // chapter markers removed at Amr's request
  if (o.type === "chapter") return null;
  return (
    <div style={{ ...box, left: layout.sideMargin, right: undefined, top: layout.labelY, textAlign: "left" }}>
      <Eyebrow>{o.text}</Eyebrow>
    </div>
  );
};

export const CaptionText: React.FC<{ c: Caption; layout: PlatformLayout }> = ({ c, layout }) => {
  const frame = useCurrentFrame();
  const d = c.to - c.from;
  const opacity = interpolate(frame, [d - 3, d], [1, 0], clamp);
  const rightInset = layout.rightRail.w > 0 ? 1080 - layout.rightRail.x : layout.sideMargin;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: layout.sideMargin,
          right: Math.max(layout.sideMargin, rightInset),
          top: layout.captionCenterY - 80,
          height: 160,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
          textAlign: "center",
          color: colors.text,
          textShadow: colors.softShadow,
        }}
      >
        <Words text={c.text} size={58} />
      </div>
    </AbsoluteFill>
  );
};

/** Light vignette + top/bottom gradients so ivory type always reads (airy, Privilee-like). */
export const TextScrim: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 90% 75% at 50% 48%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.16) 100%)" }} />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(0,0,0,0.40) 0%, rgba(0,0,0,0.18) 26%, rgba(0,0,0,0) 42%, rgba(0,0,0,0) 54%, rgba(0,0,0,0.18) 64%, rgba(0,0,0,0.34) 76%, rgba(0,0,0,0.14) 90%, rgba(0,0,0,0) 100%)",
      }}
    />
  </AbsoluteFill>
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
