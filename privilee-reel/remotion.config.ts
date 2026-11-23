import { Config } from "@remotion/cli/config";

// processed/ holds graded intermediates, narration, fonts and brand assets that the
// composition reads with staticFile(). Originals in media/ are never touched.
Config.setPublicDir("processed");
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(95);
Config.setPixelFormat("yuv420p");
Config.setCodec("h264");
Config.setCrf(18);
Config.setColorSpace("bt709");
Config.setOverwriteOutput(true);
// Use the Chromium headless shell already installed in this environment.
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE);
}
