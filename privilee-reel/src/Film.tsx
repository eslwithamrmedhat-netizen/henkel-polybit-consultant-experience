import React from "react";
import { AbsoluteFill, Audio, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { OfferCard } from "./OfferCard";
import { Shot } from "./Shot";
import { CaptionText, Guides, OverlayText } from "./Text";
import { colors, FONT, loadFonts } from "./theme";
import { FilmProps } from "./types";

loadFonts();

const RAMP = 8; // frames for music ducking in/out around speech

const duckLevel = (f: number, speech: [number, number][], duckTo: number) => {
  let level = 1;
  for (const [a, b] of speech) {
    if (f < a - RAMP || f > b + RAMP) continue;
    const t = f < a ? (a - f) / RAMP : f > b ? (f - b) / RAMP : 0;
    level = Math.min(level, duckTo + (1 - duckTo) * t);
  }
  return level;
};

const Coverage: React.FC = () => (
  // Neutral editorial graphic for the Qatar coverage beat — no fake travel footage.
  <AbsoluteFill style={{ background: `linear-gradient(180deg, ${colors.sand} 0%, ${colors.sandDeep} 100%)` }} />
);

/** Supplied brand screenshot, contained at its own proportions and colours (never stretched or recoloured). */
const BrandCard: React.FC<{ src: string; w: number | null; h: number | null }> = ({ src, w, h }) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.22, 1, 0.36, 1) });
  const width = Math.min(420, Math.round((w ?? 300) * 1.35)); // modest upscale only — source is a small screenshot
  const height = Math.round(width * ((h ?? 300) / (w ?? 300)));
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${colors.sand} 0%, ${colors.sandDeep} 100%)`, alignItems: "center" }}>
      <Img
        src={staticFile(src)}
        style={{ position: "absolute", top: 560, width, height, borderRadius: 36, boxShadow: "0 18px 50px rgba(0,0,0,0.18)", opacity: a, transform: `scale(${0.96 + 0.04 * a})` }}
      />
    </AbsoluteFill>
  );
};

export const Film: React.FC<FilmProps> = (p) => {
  const { durationInFrames } = useVideoConfig();
  const coverageBlank = (from: number) =>
    p.shots.some((s) => s.kind === "coverage" && !s.src && from >= s.from && from < s.from + s.durationInFrames);
  const offerShot = p.shots.find((s) => s.kind === "offer");

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {p.shots.map((s) => (
        <Sequence key={`${s.id}-${s.from}`} from={s.from} durationInFrames={s.durationInFrames} name={s.id}>
          {s.kind === "coverage" && !s.src ? <Coverage /> : s.kind === "brand" && s.src ? <BrandCard src={s.src} w={s.mediaWidth} h={s.mediaHeight} /> : <Shot shot={s} ambience={p.ambience} />}
        </Sequence>
      ))}

      {offerShot && p.offer ? (
        <Sequence from={offerShot.from} durationInFrames={offerShot.durationInFrames} name="offer-card">
          <OfferCard offer={p.offer} layout={p.platform} durationInFrames={offerShot.durationInFrames} />
        </Sequence>
      ) : null}

      {p.overlays.map((o, i) => (
        <Sequence key={`o${i}`} from={o.from} durationInFrames={o.durationInFrames} name={`${o.type}: ${o.text.replace(/\n/g, " ")}`}>
          <OverlayText o={o} layout={p.platform} onLightCard={o.type === "coverage" && coverageBlank(o.from)} />
        </Sequence>
      ))}

      {p.captions.map((c, i) => (
        <Sequence key={`c${i}`} from={c.from} durationInFrames={Math.max(1, c.to - c.from)} name={`cap: ${c.text}`}>
          <CaptionText c={c} layout={p.platform} />
        </Sequence>
      ))}

      {p.voiceover ? (
        <Sequence from={p.voiceover.startFrame} name="voiceover">
          <Audio src={staticFile(p.voiceover.src)} volume={p.voiceover.volume} />
        </Sequence>
      ) : null}

      {p.music ? (
        <Audio
          src={staticFile(p.music.src)}
          volume={(f) => {
            const m = p.music!;
            const fade = Math.min(
              interpolate(f, [0, m.fadeIn], [0, 1], { extrapolateRight: "clamp" }),
              interpolate(f, [durationInFrames - m.fadeOut, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            );
            return m.volume * fade * duckLevel(f, p.speech, m.duckTo);
          }}
        />
      ) : null}

      {p.showGuides ? <Guides layout={p.platform} /> : null}
      {p.isTemplate ? (
        <div style={{ position: "absolute", top: 40, left: 0, right: 0, textAlign: "center", fontFamily: FONT, fontSize: 26, letterSpacing: "0.16em", color: "rgba(255,255,255,0.75)" }}>
          TEMPLATE PREVIEW · NOT A DELIVERABLE
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
