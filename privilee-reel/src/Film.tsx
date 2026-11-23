import React from "react";
import { AbsoluteFill, Audio, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { OfferCard } from "./OfferCard";
import { PhoneOpen } from "./PhoneOpen";
import { Shot } from "./Shot";
import { CaptionText, Guides, OverlayText, TextScrim } from "./Text";
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

/**
 * Full-bleed brand moment: the supplied app-icon screenshot (own proportions/colours, never recoloured)
 * over a blurred, darkened version of the next real shot so the frame is always filled with footage.
 */
const BrandCard: React.FC<{ src: string; w: number | null; h: number | null; backdrop: string | null }> = ({ src, w, h, backdrop }) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.22, 1, 0.36, 1) });
  const width = Math.min(440, Math.round((w ?? 300) * 1.4)); // modest upscale only — source is a small screenshot
  const height = Math.round(width * ((h ?? 300) / (w ?? 300)));
  return (
    <AbsoluteFill style={{ background: "#1d2a44", alignItems: "center" }}>
      {backdrop ? (
        <Img src={staticFile(backdrop)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", filter: "blur(34px) brightness(0.55) saturate(0.9)", transform: `scale(${1.18 - 0.03 * a})` }} />
      ) : null}
      <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 42%, rgba(255,255,255,0.10) 0%, rgba(0,0,0,0) 45%)" }} />
      <Img
        src={staticFile(src)}
        style={{ position: "absolute", top: 520, width, height, borderRadius: 40, boxShadow: "0 30px 80px rgba(0,0,0,0.45)", opacity: a, transform: `translateY(${(1 - a) * 18}px)` }}
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
          {s.kind === "coverage" && !s.src ? <Coverage /> : s.kind === "phone" && s.phone ? <PhoneOpen spec={s.phone} durationInFrames={s.durationInFrames} /> : s.kind === "brand" && s.src ? <BrandCard src={s.src} w={s.mediaWidth} h={s.mediaHeight} backdrop={s.backdrop ?? null} /> : <Shot shot={s} ambience={p.ambience} />}
        </Sequence>
      ))}

      {offerShot && p.offer ? (
        <Sequence from={offerShot.from} durationInFrames={offerShot.durationInFrames} name="offer-card">
          <OfferCard offer={p.offer} layout={p.platform} durationInFrames={offerShot.durationInFrames} />
        </Sequence>
      ) : null}

      {p.overlays.length || p.captions.length ? <TextScrim /> : null}

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
