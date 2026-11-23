export type Rect = { x: number; y: number; w: number; h: number };

export type PlatformLayout = {
  name: string;
  label: string;
  topUnsafe: number;
  bottomUnsafe: number;
  rightRail: Rect;
  sideMargin: number;
  hookCenterY: number;
  titleCenterY: number;
  captionCenterY: number;
  labelY: number;
};

export type ShotProps = {
  id: string;
  beat: string;
  kind: "video" | "image" | "coverage" | "offer";
  from: number;
  durationInFrames: number;
  src: string | null;
  mediaWidth: number | null;
  mediaHeight: number | null;
  crop: { x: number; y: number; zoom: number };
  move: { from: number; to: number } | null;
  layout: "cover" | "framed";
  clipVolume: number;
  playbackRate: number;
  transitionIn: number;
  fadeOut: number;
  /** Privacy masks in composition-normalised coords (0..1) — QR codes, account details. */
  masks: Rect[];
  hasAudio: boolean;
  trimBefore?: number;
};

export type Overlay = {
  type: "hook" | "title" | "coverage" | "label" | "brand" | "line";
  text: string;
  from: number;
  durationInFrames: number;
};

export type Caption = { text: string; from: number; to: number };

export type OfferProps = {
  eyebrow: string;
  headline: string;
  qualifier: string;
  cta: string;
  artwork: string | null;
  reviewBadge: string | null;
  showText: boolean;
};

export type FilmProps = {
  renderId: string;
  variant: string;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  platform: PlatformLayout;
  shots: ShotProps[];
  overlays: Overlay[];
  captions: Caption[];
  voiceover: { src: string; startFrame: number; volume: number } | null;
  speech: [number, number][];
  music: { src: string; volume: number; duckTo: number; fadeIn: number; fadeOut: number } | null;
  ambience: boolean;
  offer: OfferProps | null;
  showGuides: boolean;
  isTemplate: boolean;
  textLedReview?: boolean;
};

export type CoverProps = {
  title: string;
  shot: ShotProps;
  width: number;
  height: number;
  isTemplate: boolean;
};
