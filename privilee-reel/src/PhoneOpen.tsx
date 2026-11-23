import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { PhoneSpec } from "./types";

/**
 * Real app moment built ONLY from Amr's own screenshots:
 *   home screen (other apps softly defocused — Privilee stays the hero, badges unreadable)
 *   → push in + tap on the Privilee icon → launch zoom into Privilee's real splash
 *   → real app home → real Categories screen scrolling → tap "Gyms & studios".
 * Nothing in the app is invented; status bar (call timer/battery) is cropped off the splash.
 */
const W = 1080;
const H = 1920;
const ease = Easing.bezier(0.33, 0, 0.15, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const PhoneOpen: React.FC<{ spec: PhoneSpec; durationInFrames: number }> = ({ spec, durationInFrames }) => {
  const f = useCurrentFrame();
  const d = durationInFrames;
  const [hw, hh] = spec.homeSize;
  const k = W / hw;
  const homeH = hh * k;
  const ty = (H - homeH) / 2;
  const [x0, y0, x1, y1] = spec.iconRect;
  const iconSize = (x1 - x0) * hw * k;
  const IX = ((x0 + x1) / 2) * W;
  const IY = ty + ((y0 + y1) / 2) * homeH;

  // timing (fractions of the shot so the cutdown can run it faster)
  const tPush = Math.round(d * 0.24);
  const tTap = tPush - 5;
  const tOpen0 = tPush + 1;
  const tOpen1 = Math.round(d * 0.36);
  const tScreens = Math.round(d * 0.45);

  const push = interpolate(f, [0, tPush], [1.4, 1.75], { ...clamp, easing: ease }); // starts zoomed so the short home-screen capture fills 9:16
  const defocus = interpolate(f, [0, 8], [3, 12], clamp);
  const press = interpolate(f, [tTap, tTap + 3, tTap + 7], [1, 0.9, 1], clamp);
  const ripple = interpolate(f, [tTap, tTap + 10], [0, 1], clamp);
  const open = interpolate(f, [tOpen0, tOpen1], [0, 1], { ...clamp, easing: ease });

  const startSize = iconSize * push;
  const rw = interpolate(open, [0, 1], [startSize, W]);
  const rh = interpolate(open, [0, 1], [startSize, H]);
  const cx = interpolate(open, [0, 1], [IX, W / 2]);
  const cy = interpolate(open, [0, 1], [IY, H / 2]);
  const radius = interpolate(open, [0, 1], [startSize * 0.225, 0]);
  const iconFade = interpolate(open, [0, 0.45], [1, 0], clamp);

  // screens after the splash, split by weight
  const total = spec.screens.reduce((s, x) => s + x.weight, 0);
  let acc = tScreens;
  const screenSpans = spec.screens.map((s) => {
    const len = Math.round(((d - tScreens) * s.weight) / total);
    const span = { ...s, from: acc, to: acc + len };
    acc += len;
    return span;
  });
  const active = screenSpans.find((s) => f >= s.from && f < s.to) ?? (f >= tScreens ? screenSpans[screenSpans.length - 1] : null);

  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      {/* 1 · real home screen, pushed in on Privilee; everything else softly out of focus */}
      {f < tOpen1 ? (
        <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: `${IX}px ${IY}px` }}>
          <Img src={staticFile(spec.home)} style={{ position: "absolute", left: 0, top: ty, width: W, height: homeH, filter: `blur(${defocus}px) brightness(0.72)` }} />
          <div style={{ position: "absolute", left: IX - iconSize / 2, top: IY - iconSize / 2, width: iconSize, height: iconSize, transform: `scale(${press})` }}>
            <Img src={staticFile(spec.icon)} style={{ width: "100%", height: "100%", borderRadius: iconSize * 0.225, boxShadow: "0 10px 30px rgba(0,0,0,0.45)", display: "block" }} />
            {ripple > 0 && ripple < 1 ? (
              <div style={{ position: "absolute", left: iconSize / 2 - 70 * (1 + ripple), top: iconSize / 2 - 70 * (1 + ripple), width: 140 * (1 + ripple), height: 140 * (1 + ripple), borderRadius: "50%", background: `rgba(255,255,255,${0.35 * (1 - ripple)})` }} />
            ) : null}
          </div>
        </AbsoluteFill>
      ) : null}

      {/* 2 · launch: icon grows into Privilee's real splash screen */}
      {open > 0 && f < tScreens + 2 ? (
        <div style={{ position: "absolute", left: cx - rw / 2, top: cy - rh / 2, width: rw, height: rh, borderRadius: radius, overflow: "hidden", background: "#5f85b8" }}>
          <Img src={staticFile(spec.splash)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
          <Img src={staticFile(spec.icon)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: iconFade }} />
        </div>
      ) : null}

      {/* 3 · real app screens with a gentle scroll; tap on the highlighted tile */}
      {active ? <Screen s={active} f={f} /> : null}
    </AbsoluteFill>
  );
};

const Screen: React.FC<{ s: PhoneSpec["screens"][number] & { from: number; to: number }; f: number }> = ({ s, f }) => {
  const local = f - s.from;
  const len = s.to - s.from;
  const dispH = (W * s.size[1]) / s.size[0];
  const maxScroll = Math.max(0, dispH - H);
  const scroll = interpolate(local, [0, len * (s.tap ? 0.6 : 1)], [0, maxScroll * (s.scroll ?? 0.5)], { ...clamp, easing: ease });
  const enter = interpolate(local, [0, 6], [40, 0], { ...clamp, easing: ease });
  const enterO = interpolate(local, [0, 5], [0, 1], clamp);
  const tapT = s.tap ? interpolate(local, [len * 0.66, len * 0.66 + 4, len * 0.66 + 9], [1, 0.95, 1], clamp) : 1;
  const tapGlow = s.tap ? interpolate(local, [len * 0.66, len * 0.66 + 6, len], [0, 0.35, 0.18], clamp) : 0;
  return (
    <AbsoluteFill style={{ background: "#fff", opacity: enterO }}>
      <div style={{ position: "absolute", left: 0, top: -scroll + enter, width: W, height: dispH }}>
        <Img src={staticFile(s.src)} style={{ width: W, height: dispH, display: "block" }} />
        {s.tap ? (
          <div
            style={{
              position: "absolute",
              left: s.tap[0] * W,
              top: s.tap[1] * dispH,
              width: (s.tap[2] - s.tap[0]) * W,
              height: (s.tap[3] - s.tap[1]) * dispH,
              borderRadius: 28,
              transform: `scale(${tapT})`,
              background: `rgba(0,0,0,${tapGlow})`,
              boxShadow: tapGlow > 0 ? `0 0 0 6px rgba(255,255,255,${tapGlow * 2})` : "none",
            }}
          />
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
