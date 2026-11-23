import { continueRender, delayRender, staticFile } from "remotion";

/**
 * Editorial pairing (both SIL OFL, files in processed/fonts/):
 *  - SERIF  Playfair Display — hook, titles, places (italics for emphasis)
 *  - SANS   Manrope — supporting lines, captions, tracked eyebrows
 */
export const SERIF = "'Playfair Display', Georgia, serif";
export const SANS = "Manrope, 'Helvetica Neue', Arial, sans-serif";
export const FONT = SANS;

export const colors = {
  text: "#FBF8F3", // warm white, never pure #fff on sunlit footage
  ink: "#1F1D1A",
  sand: "#ECE5DA",
  sandDeep: "#D9CEBF",
  shadow: "0 2px 22px rgba(0,0,0,0.42), 0 1px 3px rgba(0,0,0,0.45)",
  softShadow: "0 1px 18px rgba(0,0,0,0.55), 0 1px 2px rgba(0,0,0,0.6)",
  captionBg: "rgba(14,13,12,0.40)",
  review: "#B3261E",
};

const faces: [string, string, string, string][] = [
  ["Playfair Display", "400", "normal", "playfair-display-latin-400-normal.woff2"],
  ["Playfair Display", "500", "normal", "playfair-display-latin-500-normal.woff2"],
  ["Playfair Display", "600", "normal", "playfair-display-latin-600-normal.woff2"],
  ["Playfair Display", "400", "italic", "playfair-display-latin-400-italic.woff2"],
  ["Playfair Display", "500", "italic", "playfair-display-latin-500-italic.woff2"],
  ["Playfair Display", "600", "italic", "playfair-display-latin-600-italic.woff2"],
  ["Manrope", "400", "normal", "manrope-latin-400-normal.woff2"],
  ["Manrope", "500", "normal", "manrope-latin-500-normal.woff2"],
  ["Manrope", "600", "normal", "manrope-latin-600-normal.woff2"],
  ["Manrope", "700", "normal", "manrope-latin-700-normal.woff2"],
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
