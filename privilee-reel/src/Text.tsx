import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { colors, SANS, SERIF } from "./theme";
import { Caption, Overlay, PlatformLayout } from "./types";

const ease = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Exit: quick fade + small lift. Every text element shares it. */
const useExit = (d: number, outF = 7) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [d - outF, d], [1, 0], clamp);
  const y = interpolate(frame, [d - outF, d], [0, -10], clamp);
  return { o, y };
};

/** A headline line revealed from behind a mask (slides up out of its own baseline). */
const MaskLine: React.FC<{ delay: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delay, children, style }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 16], [0, 1], { ...clamp, easing: ease });
  return (
    <div style={{ overflow: "hidden", paddingBottom: "0.12em", marginBottom: "-0.12em" }}>
      <div style={{ transform: `translateY(${(1 - t) * 105}%)`, ...style }}>{children}</div>
    </div>
  );
};

/** Tracked uppercase label that "settles" its letter-spacing as it appears. */
const Eyebrow: React.FC<{ children: React.ReactNode; delay?: number; color?: string }> = ({ children, delay = 0, color = colors.text }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 18], [0, 1], { ...clamp, easing: ease });
  return (
    <div
      style={{
        fontFamily: SANS,
        fontWeight: 800,
        fontSize: 34,
        letterSpacing: `${0.46 - 0.12 * t}em`,
        textTransform: "uppercase",
        color,
        opacity: t,
        marginBottom: 14,
        textShadow: colors.softShadow,
      }}
    >
      {children}
    </div>
  );
};

/** Supporting line: words rise in one after another (no bouncing). */
const Words: React.FC<{ text: string; size: number; delay?: number }> = ({ text, size, delay = 0 }) => {
  const frame = useCurrentFrame();
  return (
    <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: size, lineHeight: 1.18, letterSpacing: "-0.012em" }}>
      {text.split(" ").map((w, i) => {
        const t = interpolate(frame, [delay + i * 2, delay + i * 2 + 10], [0, 1], { ...clamp, easing: ease });
        return (
          <span key={i} style={{ display: "inline-block", opacity: t, transform: `translateY(${(1 - t) * 22}px)`, marginRight: "0.26em" }}>
            {w}
          </span>
        );
      })}
    </span>
  );
};

const Rule: React.FC<{ delay: number }> = ({ delay }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 18], [0, 1], { ...clamp, easing: ease });
  return <div style={{ width: 72 * t, height: 3, background: colors.accent, margin: "30px auto 0", borderRadius: 2 }} />;
};

/** Two-tone serif: first line upright ivory, second line italic champagne. */
const SerifPair: React.FC<{ a: string; b?: string; size: number }> = ({ a, b, size }) => (
  <div style={{ fontFamily: SERIF, fontSize: size, lineHeight: 1.0, letterSpacing: "-0.018em", textShadow: colors.shadow }}>
    <MaskLine delay={0} style={{ fontWeight: 600, color: colors.text }}>
      {a}
    </MaskLine>
    {b ? (
      <MaskLine delay={5} style={{ fontWeight: 500, fontStyle: "italic", color: colors.accent }}>
        {b}
      </MaskLine>
    ) : null}
  </div>
);

/** "01|The workweek" — small editorial chapter marker, top-left inside the safe area. */
const ChapterMark: React.FC<{ text: string; layout: PlatformLayout; exitO: number }> = ({ text, layout, exitO }) => {
  const [num, name] = text.split("|");
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, 16], [0, 1], { ...clamp, easing: ease });
  return (
    <div style={{ position: "absolute", left: layout.sideMargin, top: layout.labelY - 40, opacity: exitO * t, display: "flex", alignItems: "center", gap: 18, textShadow: colors.softShadow }}>
      <span style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, fontSize: 52, color: colors.accent }}>{num}</span>
      <span style={{ width: 54 * t, height: 2, background: colors.text, opacity: 0.85 }} />
      <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 26, letterSpacing: "0.34em", textTransform: "uppercase", color: colors.text }}>{name}</span>
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
    color: colors.text,
    opacity: exitO,
    transform: `translateY(${exitY}px)`,
  };
  const lines = o.text.split("\n");

  if (o.type === "hook") {
    if (lines.length === 2 && /\.$/.test(lines[0])) {
      // "Different cities. / Same routine."
      return (
        <div style={{ ...box, top: layout.hookCenterY - 130 }}>
          <SerifPair a={lines[0]} b={lines[1]} size={112} />
        </div>
      );
    }
    // "My best / Dubai life hack"  →  MY BEST · Dubai (upright) · life hack (italic champagne)
    const words = lines.slice(1).join(" ").split(" ");
    return (
      <div style={{ ...box, top: layout.hookCenterY - 150 }}>
        <Eyebrow>{lines[0]}</Eyebrow>
        <SerifPair a={words[0]} b={words.slice(1).join(" ")} size={138} />
      </div>
    );
  }
  if (o.type === "title") {
    return (
      <div style={{ ...box, top: layout.titleCenterY - 150 }}>
        <SerifPair a={lines[0]} b={lines[1]} size={112} />
        <Rule delay={14} />
      </div>
    );
  }
  if (o.type === "coverage") {
    const place = lines.slice(1).join(" ").replace(/ and /, " & ");
    const [p1, p2] = place.split(" & ");
    return (
      <div style={{ ...box, top: 760 }}>
        <Eyebrow>{lines[0]}</Eyebrow>
        <div style={{ fontFamily: SERIF, fontSize: 124, lineHeight: 1.0, letterSpacing: "-0.018em", textShadow: colors.shadow }}>
          <MaskLine delay={3} style={{ fontWeight: 600 }}>
            {p1}
            {p2 ? (
              <>
                <span style={{ fontStyle: "italic", fontWeight: 500, color: colors.accent }}> &amp; </span>
                {p2}
              </>
            ) : null}
          </MaskLine>
        </div>
      </div>
    );
  }
  if (o.type === "chapter") {
    return <ChapterMark text={o.text} layout={layout} exitO={exitO} />;
  }
  if (o.type === "line") {
    return (
      <div style={{ ...box, top: layout.captionCenterY - 80, height: 160, display: "flex", alignItems: "center", justifyContent: "center", textShadow: o.boxed ? "none" : colors.softShadow }}>
        <span style={o.boxed ? { background: "rgba(16,22,34,0.66)", backdropFilter: "blur(14px)", padding: "16px 32px 18px", borderRadius: 28 } : {}}>
          <Words text={o.text} size={56} />
        </span>
      </div>
    );
  }
  // label / brand
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
          top: layout.captionCenterY - 70,
          height: 140,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
          textAlign: "center",
          color: colors.text,
          textShadow: colors.softShadow,
        }}
      >
        <Words text={c.text} size={54} />
      </div>
    </AbsoluteFill>
  );
};

/** Cinematic finish: edge vignette + top/bottom gradients so ivory type always reads. */
export const TextScrim: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 90% 75% at 50% 48%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.16) 100%)" }} />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(0,0,0,0.38) 0%, rgba(0,0,0,0.16) 24%, rgba(0,0,0,0) 38%, rgba(0,0,0,0) 54%, rgba(0,0,0,0.18) 64%, rgba(0,0,0,0.34) 76%, rgba(0,0,0,0.14) 90%, rgba(0,0,0,0) 100%)",
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
