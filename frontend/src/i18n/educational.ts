import type { MessageKey } from "./messages";

export const educationalTextKeys = {
  probability: "education.probability",
  liquidity: "education.liquidity",
  volume: "education.volume",
  stale: "education.stale",
  resolution: "education.resolution",
  quality: "education.quality",
  change: "education.change",
  system: "education.system",
  replay: "education.replay",
} satisfies Record<string, MessageKey>;
