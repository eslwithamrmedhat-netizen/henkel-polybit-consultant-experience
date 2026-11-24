export type Rect = { x: number; y: number; w: number; h: number; blur?: boolean };

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
  kind: "video" | "image" | "coverage" | "offer" | "brand" | "phone";
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
  /** brand cards: a processed still shown blurred behind the logo so the frame is full */
  backdrop?: string | null;
  /** phone shots: real app-moment assets */
  phone?: PhoneSpec;
};

export type PhoneSpec = {
  home: string;
  homeSize: [number, number];
  iconRect: [number, number, number, number];
  icon: string;
  splash: string;
  screens: { src: string; size: [number, number]; weight: number; scroll?: number; tap?: [number, number, number, number] }[];
};

export type Overlay = {
  type: "hook" | "title" | "coverage" | "label" | "brand" | "line" | "chapter";
  text: string;
  /** frosted backing for lines that sit over light UI (e.g. app screens) */
  boxed?: boolean;
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
  scriptFont?: string;
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
