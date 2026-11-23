import { continueRender, delayRender, staticFile } from "remotion";

/**
 * Bold editorial type system (all SIL OFL; files + licences in processed/fonts/):
 *  - DISPLAY  Anton — heavy condensed capitals: the punch (hook, titles, places)
 *  - SCRIPT   Instrument Serif Italic — the elegant accent word(s), in champagne
 *  - SANS     Inter Tight — supporting lines, captions, tracked labels
 */
export const DISPLAY = "Anton, 'Arial Narrow', sans-serif";
export const SCRIPT = "'Instrument Serif', Georgia, serif";
export const SANS = "'Inter Tight', 'Helvetica Neue', Arial, sans-serif";
export const SERIF = DISPLAY; // legacy alias (offer card / cover headline)
export const FONT = SANS;

export const colors = {
  text: "#F7F3EA",
  accent: "#E9D3A3",
  ink: "#1F1D1A",
  sand: "#ECE5DA",
  sandDeep: "#D9CEBF",
  shadow: "0 4px 34px rgba(0,0,0,0.45), 0 1px 3px rgba(0,0,0,0.5)",
  softShadow: "0 2px 22px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.65)",
  captionBg: "rgba(14,13,12,0.40)",
  review: "#B3261E",
};

const faces: [string, string, string, string][] = [
  ["Anton", "400", "normal", "anton-latin-400-normal.woff2"],
  ["Instrument Serif", "400", "normal", "instrument-serif-latin-400-normal.woff2"],
  ["Instrument Serif", "400", "italic", "instrument-serif-latin-400-italic.woff2"],
  ["Inter Tight", "500", "normal", "inter-tight-latin-500-normal.woff2"],
  ["Inter Tight", "600", "normal", "inter-tight-latin-600-normal.woff2"],
  ["Inter Tight", "700", "normal", "inter-tight-latin-700-normal.woff2"],
  ["Inter Tight", "800", "normal", "inter-tight-latin-800-normal.woff2"],
];

let loaded = false;
export const loadFonts = () => {
  if (loaded || typeof document === "undefined") return;
  loaded = true;
  const handle = delayRender("Loading fonts");
  Promise.all(
    faces.map(([family, weight, style, file]) => {
      const face = new FontFace(family, `url(${staticFile(`fonts/${file}`)})`, { weight, style });
      return face.load().then((f) => document.fonts.add(f));
    }),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error("Font load failed", e);
      continueRender(handle);
    });
};
