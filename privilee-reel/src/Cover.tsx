import React from "react";
import { AbsoluteFill } from "remotion";
import { Media } from "./Shot";
import { colors, DISPLAY, loadFonts, SCRIPT } from "./theme";
import { CoverProps } from "./types";

loadFonts();

/**
 * Cover from a real frame: DIFFERENT / CITIES. in heavy capitals + "same routine." in the
 * champagne italic accent. Sits in the sky above the face, inside the central band that
 * survives the 4:5 / 3:4 profile-grid crops.
 */
export const Cover: React.FC<CoverProps> = ({ title, shot }) => {
  const [a, b] = title.split("\n");
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Media shot={shot} ambience={false} still />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.12) 20%, rgba(0,0,0,0.32) 40%, rgba(0,0,0,0) 60%)" }} />
      <div style={{ position: "absolute", left: 80, right: 80, top: 430, textAlign: "center" }}>
        {a.split(" ").map((w, i) => (
          <div key={i} style={{ fontFamily: DISPLAY, fontSize: 178, lineHeight: 0.9, textTransform: "uppercase", color: colors.text, textShadow: colors.shadow }}>
            {w}
          </div>
        ))}
        {b ? (
          <div style={{ fontFamily: SCRIPT, fontStyle: "italic", fontSize: 132, lineHeight: 0.95, marginTop: -18, color: colors.accent, textShadow: colors.softShadow }}>
            {b.charAt(0).toLowerCase() + b.slice(1)}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
