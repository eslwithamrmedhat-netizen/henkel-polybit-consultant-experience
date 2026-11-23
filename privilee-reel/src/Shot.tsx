import React from "react";
import { AbsoluteFill, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { colors, FONT } from "./theme";
import { ShotProps } from "./types";

const EDGE = 6; // frames of audio fade at each cut, avoids clicks

const Slate: React.FC<{ shot: ShotProps }> = ({ shot }) => (
  <AbsoluteFill
    style={{
      background: "linear-gradient(160deg, #2a2724 0%, #151413 100%)",
      justifyContent: "center",
      alignItems: "center",
      fontFamily: FONT,
      color: "rgba(251,248,243,0.85)",
      padding: 120,
      textAlign: "center",
    }}
  >
    <div style={{ fontSize: 30, letterSpacing: "0.2em", opacity: 0.6 }}>AWAITING MEDIA · {shot.id}</div>
    <div style={{ fontSize: 46, fontWeight: 600, marginTop: 28, lineHeight: 1.25 }}>{shot.beat}</div>
    <div style={{ fontSize: 28, marginTop: 28, opacity: 0.5 }}>
      {shot.kind} · {(shot.durationInFrames / 30).toFixed(1)} s
    </div>
  </AbsoluteFill>
);

export const Media: React.FC<{ shot: ShotProps; ambience: boolean; still?: boolean }> = ({ shot, ambience, still }) => {
  const frame = useCurrentFrame();
  const d = shot.durationInFrames;
  const moveScale = shot.move && !still ? interpolate(frame, [0, d], [shot.move.from, shot.move.to], { extrapolateRight: "clamp" }) : 1;
  const scale = shot.crop.zoom * moveScale;
  const pos = `${shot.crop.x * 100}% ${shot.crop.y * 100}%`;
  const framed = shot.layout === "framed";
  const style: React.CSSProperties = framed
    ? { width: "100%", height: "100%", objectFit: "contain", transform: `scale(${moveScale})` }
    : { width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${scale})`, transformOrigin: pos };

  if (!shot.src) return <Slate shot={shot} />;

  const isVideo = shot.kind !== "image" && /\.(mp4|mov|m4v)$/i.test(shot.src);
  const vol = (f: number) =>
    ambience && shot.hasAudio
      ? shot.clipVolume * interpolate(f, [0, EDGE, d - EDGE, d], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
      : 0;

  const el = isVideo ? (
    <OffthreadVideo
      src={staticFile(shot.src)}
      trimBefore={shot.trimBefore ?? 0}
      playbackRate={shot.playbackRate}
      volume={vol}
      muted={!ambience || !shot.hasAudio || shot.clipVolume === 0}
      style={style}
    />
  ) : (
    <Img src={staticFile(shot.src)} style={style} />
  );

  if (!framed) return <AbsoluteFill style={{ overflow: "hidden" }}>{el}</AbsoluteFill>;
  // Intentional layout for landscape material: contained, never stretched or cropped through the action.
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${colors.sand} 0%, ${colors.sandDeep} 100%)` }}>
      <div style={{ position: "absolute", left: 48, right: 48, top: 520, height: 620, borderRadius: 18, overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,0.18)" }}>
        {el}
      </div>
    </AbsoluteFill>
  );
};

export const Shot: React.FC<{ shot: ShotProps; ambience: boolean }> = ({ shot, ambience }) => {
  const frame = useCurrentFrame();
  const d = shot.durationInFrames;
  const fadeIn = shot.transitionIn > 0 ? interpolate(frame, [0, shot.transitionIn], [0, 1], { extrapolateRight: "clamp" }) : 1;
  const fadeOut = shot.fadeOut > 0 ? interpolate(frame, [d - shot.fadeOut, d], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  return (
    <AbsoluteFill style={{ opacity: fadeIn }}>
      <Media shot={shot} ambience={ambience} />
      {shot.masks.map((m, i) =>
        m.blur ? (
          // soft privacy blur (e.g. a bystander's face) — keeps the scene, removes identity
          <div
            key={i}
            style={{ position: "absolute", left: `${m.x * 100}%`, top: `${m.y * 100}%`, width: `${m.w * 100}%`, height: `${m.h * 100}%`, borderRadius: "50%", backdropFilter: "blur(26px)", WebkitBackdropFilter: "blur(26px)", background: "rgba(120,110,100,0.12)" }}
          />
        ) : (
          <div
            key={i}
            style={{ position: "absolute", left: `${m.x * 100}%`, top: `${m.y * 100}%`, width: `${m.w * 100}%`, height: `${m.h * 100}%`, borderRadius: 16, background: "rgba(16,16,20,0.95)", backdropFilter: "blur(30px)" }}
          />
        ),
      )}
      {fadeOut < 1 ? <AbsoluteFill style={{ background: "#000", opacity: 1 - fadeOut }} /> : null}
    </AbsoluteFill>
  );
};
