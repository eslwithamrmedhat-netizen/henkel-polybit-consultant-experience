import { continueRender, delayRender, staticFile } from "remotion";

/** One type family (Inter, OFL — processed/fonts/LICENSE-Inter.txt), restrained hierarchy. */
export const FONT = "Inter, 'Inter Display', system-ui, sans-serif";

export const colors = {
  text: "#FBF8F3", // warm white, never pure #fff on sunlit footage
  ink: "#1F1D1A",
  sand: "#ECE5DA",
  sandDeep: "#D9CEBF",
  shadow: "0 2px 18px rgba(0,0,0,0.38), 0 1px 3px rgba(0,0,0,0.45)",
  captionBg: "rgba(14,13,12,0.40)",
  review: "#B3261E",
};

const weights: [string, string][] = [
  ["400", "Inter-Regular.otf"],
  ["500", "Inter-Medium.otf"],
  ["600", "Inter-SemiBold.otf"],
  ["700", "Inter-Bold.otf"],
];

let loaded = false;
export const loadFonts = () => {
  if (loaded || typeof document === "undefined") return;
  loaded = true;
  const handle = delayRender("Loading Inter");
  Promise.all(
    weights.map(([w, file]) => {
      const face = new FontFace("Inter", `url(${staticFile(`fonts/${file}`)})`, { weight: w });
      return face.load().then((f) => document.fonts.add(f));
    }),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error("Font load failed", e);
      continueRender(handle);
    });
};
