import { continueRender, delayRender, staticFile } from "remotion";

/**
 * Editorial type system (both SIL OFL, files + licences in processed/fonts/):
 *  - SERIF  Fraunces — sturdy, warm display serif for hook, titles, places, cover
 *  - SANS   Plus Jakarta Sans — confident supporting lines, captions, tracked labels
 * Colour: warm ivory text; champagne for italic emphasis (used sparingly).
 */
export const SERIF = "Fraunces, Georgia, serif";
export const SANS = "'Plus Jakarta Sans', 'Helvetica Neue', Arial, sans-serif";
export const FONT = SANS;

export const colors = {
  text: "#F6F1E6",
  accent: "#E8D2A2",
  ink: "#1F1D1A",
  sand: "#ECE5DA",
  sandDeep: "#D9CEBF",
  shadow: "0 2px 30px rgba(0,0,0,0.50), 0 1px 3px rgba(0,0,0,0.55)",
  softShadow: "0 2px 22px rgba(0,0,0,0.60), 0 1px 2px rgba(0,0,0,0.65)",
  captionBg: "rgba(14,13,12,0.40)",
  review: "#B3261E",
};

const faces: [string, string, string, string][] = [
  ["Fraunces", "500", "normal", "fraunces-latin-500-normal.woff2"],
  ["Fraunces", "600", "normal", "fraunces-latin-600-normal.woff2"],
  ["Fraunces", "700", "normal", "fraunces-latin-700-normal.woff2"],
  ["Fraunces", "500", "italic", "fraunces-latin-500-italic.woff2"],
  ["Fraunces", "600", "italic", "fraunces-latin-600-italic.woff2"],
  ["Fraunces", "700", "italic", "fraunces-latin-700-italic.woff2"],
  ["Plus Jakarta Sans", "500", "normal", "plus-jakarta-sans-latin-500-normal.woff2"],
  ["Plus Jakarta Sans", "600", "normal", "plus-jakarta-sans-latin-600-normal.woff2"],
  ["Plus Jakarta Sans", "700", "normal", "plus-jakarta-sans-latin-700-normal.woff2"],
  ["Plus Jakarta Sans", "800", "normal", "plus-jakarta-sans-latin-800-normal.woff2"],
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
