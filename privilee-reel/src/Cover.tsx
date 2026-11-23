import React from "react";
import { AbsoluteFill } from "remotion";
import { Media } from "./Shot";
import { colors, loadFonts, SERIF } from "./theme";
import { CoverProps } from "./types";

loadFonts();

/**
 * Cover from a real frame. Title sits in the central 1080x1350 band so it survives the
 * 4:5 / 3:4 profile-grid crops; keep the face in the same band via the shot's crop.y.
 */
export const Cover: React.FC<CoverProps> = ({ title, shot }) => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    <Media shot={shot} ambience={false} still />
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 45%, rgba(0,0,0,0.38) 100%)" }} />
    <div
      style={{
        position: "absolute",
        left: 90,
        right: 90,
        top: 1120,
        textAlign: "center",
        fontFamily: SERIF,
        fontWeight: 500,
        fontSize: 98,
        lineHeight: 1.02,
        color: colors.text,
        textShadow: colors.shadow,
      }}
    >
      {title.split("\n").map((l, i) => (
        <div key={i} style={{ fontStyle: i === 1 ? "italic" : "normal", fontWeight: i === 1 ? 400 : 500 }}>
          {l}
        </div>
      ))}
    </div>
  </AbsoluteFill>
);
