import React from "react";
import { CalculateMetadataFunction, Composition, Still } from "remotion";
import { Cover } from "./Cover";
import defaultCover from "./defaultCover.json";
import defaultFilm from "./defaultProps.json";
import { Film } from "./Film";
import { CoverProps, FilmProps } from "./types";

// Renders pass --props=processed/props/<render>.json (built by scripts/build_props.py);
// the defaults below are the template timeline so Studio opens with something useful.
const filmMeta: CalculateMetadataFunction<FilmProps> = ({ props }) => ({
  durationInFrames: Math.max(1, props.durationInFrames),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="Film"
      component={Film}
      defaultProps={defaultFilm as unknown as FilmProps}
      calculateMetadata={filmMeta}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
    />
    <Still id="Cover" component={Cover} defaultProps={defaultCover as unknown as CoverProps} width={1080} height={1920} />
  </>
);
