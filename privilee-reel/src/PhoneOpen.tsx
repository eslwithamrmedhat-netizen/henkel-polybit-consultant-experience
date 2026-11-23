import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { SANS } from "./theme";

/**
 * Generic smartphone home screen → push in on the Privilee icon → tap → app-launch zoom.
 * Deliberately generic UI (no Apple logo, wallpaper or system app icons). The ONLY real brand
 * asset is Amr's own screenshot of the Privilee icon; no Privilee app screens are invented —
 * the "opened app" is the icon on its own colour, like a launch screen.
 */

const W = 1080;
const ICON = 168;
const COLS = 4;
const MARGIN = 78;
const GAP = (W - 2 * MARGIN - COLS * ICON) / (COLS - 1);
const TOP = 230;
const PITCH = 256;
const TARGET = { col: 1, row: 2 }; // Privilee position on the grid

const ease = Easing.bezier(0.33, 0, 0.15, 1);
const iconX = (c: number) => MARGIN + c * (ICON + GAP);
const iconY = (r: number) => TOP + r * PITCH;
const TX = iconX(TARGET.col) + ICON / 2;
const TY = iconY(TARGET.row) + ICON / 2;

// muted, generic app tiles (no real brands)
const TILES: [string, string, string][] = [
  ["#ff9a8b", "#ff6a88", "Social"], ["#89f7fe", "#66a6ff", "Weather"], ["#c3cfe2", "#8e9eab", "Files"], ["#fddb92", "#f6a04d", "Notes"],
  ["#a1c4fd", "#c2e9fb", "Calendar"], ["#d4fc79", "#96e6a1", "Banking"], ["#84fab0", "#4fbf9f", "Maps"], ["#fbc2eb", "#a18cd1", "Music"],
  ["#30cfd0", "#330867", "Rides"], ["", "", "Privilee"], ["#f6d365", "#fda085", "Food"], ["#e0c3fc", "#8ec5fc", "Camera"],
  ["#43e97b", "#38a169", "Health"], ["#fa709a", "#fee140", "Shop"], ["#667eea", "#764ba2", "News"], ["#5ee7df", "#b490ca", "Travel"],
];
const DOCK: [string, string][] = [["#9be15d", "#00b16a"], ["#4facfe", "#0062ff"], ["#ffffff", "#d8dde6"], ["#ff5f6d", "#ffc371"]];

const Glyph: React.FC<{ i: number }> = ({ i }) => {
  const s: React.CSSProperties = { position: "absolute", background: "rgba(255,255,255,0.92)" };
  switch (i % 4) {
    case 0:
      return <div style={{ ...s, left: 52, top: 52, width: 64, height: 64, borderRadius: 32 }} />;
    case 1:
      return <div style={{ ...s, left: 44, top: 74, width: 80, height: 20, borderRadius: 10 }} />;
    case 2:
      return <div style={{ ...s, left: 50, top: 50, width: 68, height: 68, borderRadius: 18, background: "rgba(255,255,255,0.0)", border: "10px solid rgba(255,255,255,0.92)" }} />;
    default:
      return <div style={{ ...s, left: 64, top: 46, width: 40, height: 76, borderRadius: 20 }} />;
  }
};

const Tile: React.FC<{ a: string; b: string; i: number; size?: number }> = ({ a, b, i, size = ICON }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.225, background: `linear-gradient(145deg, ${a}, ${b})`, position: "relative", overflow: "hidden", boxShadow: "0 6px 18px rgba(0,0,0,0.18)" }}>
    <div style={{ transform: `scale(${size / ICON})`, transformOrigin: "0 0", width: ICON, height: ICON, position: "relative" }}>
      <Glyph i={i} />
    </div>
  </div>
);

const PrivileeIcon: React.FC<{ icon: string; size: number; press?: number }> = ({ icon, size, press = 1 }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.225, overflow: "hidden", transform: `scale(${press})`, boxShadow: "0 8px 22px rgba(0,0,0,0.25)", background: "#7489aa" }}>
    <Img src={staticFile(icon)} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
  </div>
);

const Label: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ width: ICON + 40, marginLeft: -20, textAlign: "center", fontFamily: SANS, fontWeight: 500, fontSize: 27, color: "#fff", marginTop: 12, textShadow: "0 1px 6px rgba(0,0,0,0.45)" }}>{text}</div>
);

export const PhoneOpen: React.FC<{ wallpaper: string | null; icon: string; durationInFrames: number }> = ({ wallpaper, icon, durationInFrames }) => {
  const f = useCurrentFrame();
  const d = durationInFrames;
  const tPush = Math.round(d * 0.42); // camera push ends
  const tTap = tPush - 4;
  const tOpen0 = tPush + 2;
  const tOpen1 = tOpen0 + 16;

  const push = interpolate(f, [0, tPush], [1, 1.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const dim = interpolate(f, [tPush - 8, tPush + 4], [0, 0.35], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const press = interpolate(f, [tTap, tTap + 3, tTap + 7], [1, 0.9, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ripple = interpolate(f, [tTap, tTap + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const open = interpolate(f, [tOpen0, tOpen1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

  // launch rect: from the (pushed) icon to full screen
  const startSize = ICON * push;
  const rw = interpolate(open, [0, 1], [startSize, W]);
  const rh = interpolate(open, [0, 1], [startSize, 1920]);
  const cx = interpolate(open, [0, 1], [TX, W / 2]);
  const cy = interpolate(open, [0, 1], [TY, 960]);
  const radius = interpolate(open, [0, 1], [startSize * 0.225, 0]);
  const centerIcon = interpolate(open, [0, 1], [startSize, 300]);
  const iconShift = interpolate(open, [0, 1], [0, -120]);
  const settle = interpolate(f, [tOpen1, d], [1, 1.03], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#0e1626", overflow: "hidden" }}>
      {/* home screen with camera push centred on the Privilee icon */}
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: `${TX}px ${TY}px` }}>
        {wallpaper ? (
          <Img src={staticFile(wallpaper)} style={{ position: "absolute", inset: -40, width: W + 80, height: 2000, objectFit: "cover", filter: "blur(22px) brightness(0.78) saturate(1.05)" }} />
        ) : null}
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.18), rgba(0,0,0,0.05) 40%, rgba(0,0,0,0.25))" }} />
        {/* status bar (generic) */}
        <div style={{ position: "absolute", top: 46, left: 96, fontFamily: SANS, fontWeight: 700, fontSize: 38, color: "#fff" }}>7:30</div>
        <div style={{ position: "absolute", top: 54, right: 90, display: "flex", gap: 14, alignItems: "flex-end" }}>
          {[12, 18, 24, 30].map((h, i) => (
            <div key={i} style={{ width: 8, height: h, borderRadius: 2, background: "#fff" }} />
          ))}
          <div style={{ marginLeft: 12, width: 60, height: 28, borderRadius: 8, border: "3px solid rgba(255,255,255,0.9)", padding: 3, boxSizing: "border-box" }}>
            <div style={{ width: "78%", height: "100%", borderRadius: 4, background: "#fff" }} />
          </div>
        </div>
        {/* app grid */}
        {TILES.map(([a, b, name], i) => {
          const c = i % COLS;
          const r = Math.floor(i / COLS);
          const isP = name === "Privilee";
          return (
            <div key={i} style={{ position: "absolute", left: iconX(c), top: iconY(r), opacity: isP ? 1 : 1 - dim }}>
              {isP ? <PrivileeIcon icon={icon} size={ICON} press={press} /> : <Tile a={a} b={b} i={i} />}
              <Label text={name} />
              {isP && ripple > 0 && ripple < 1 ? (
                <div style={{ position: "absolute", left: ICON / 2 - 60 * (1 + ripple), top: ICON / 2 - 60 * (1 + ripple), width: 120 * (1 + ripple), height: 120 * (1 + ripple), borderRadius: "50%", background: `rgba(255,255,255,${0.35 * (1 - ripple)})` }} />
              ) : null}
            </div>
          );
        })}
        {/* page dots + dock */}
        <div style={{ position: "absolute", top: 1560, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 14, opacity: 1 - dim }}>
          {[1, 0.4, 0.4].map((o, i) => (
            <div key={i} style={{ width: 14, height: 14, borderRadius: 7, background: `rgba(255,255,255,${o})` }} />
          ))}
        </div>
        <div style={{ position: "absolute", left: 36, right: 36, top: 1620, height: 228, borderRadius: 64, background: "rgba(255,255,255,0.20)", backdropFilter: "blur(20px)", display: "flex", alignItems: "center", justifyContent: "space-around", padding: "0 30px", opacity: 1 - dim }}>
          {DOCK.map(([a, b], i) => (
            <Tile key={i} a={a} b={b} i={i + 1} />
          ))}
        </div>
      </AbsoluteFill>

      {/* launch: icon tile expands to a full-screen "app" (icon on its own colour — no invented UI) */}
      {open > 0 ? (
        <div
          style={{
            position: "absolute",
            left: cx - rw / 2,
            top: cy - rh / 2,
            width: rw,
            height: rh,
            borderRadius: radius,
            overflow: "hidden",
            background: "radial-gradient(circle at 50% 38%, #8195b8 0%, #5d7299 45%, #34476e 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div style={{ transform: `translateY(${iconShift}px) scale(${settle})` }}>
            <PrivileeIcon icon={icon} size={centerIcon} />
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
