// accents.ts — harmonious oklch accent ramp per stage hue.
import type { CSSProperties } from "react";
import type { AccentName, Palette } from "./types";

export interface Accent {
  solid: string;
  text: string;
  soft: string;
  softer: string;
  line: string;
  ring: string;
}

const STAGE_HUE: Record<AccentName, number> = {
  teal: 185,
  amber: 65,
  gold: 95,
  violet: 300,
  blue: 255,
  rose: 18,
};

export function getAccent(accentName: AccentName, palette: Palette): Accent {
  if (palette === "grafito") {
    const h = 255;
    return {
      solid: `oklch(0.50 0.045 ${h})`,
      text: `oklch(0.42 0.05 ${h})`,
      soft: `oklch(0.972 0.008 ${h})`,
      softer: `oklch(0.986 0.004 ${h})`,
      line: `oklch(0.88 0.018 ${h})`,
      ring: `oklch(0.55 0.06 ${h})`,
    };
  }
  const h = STAGE_HUE[accentName] ?? 255;
  return {
    solid: `oklch(0.585 0.115 ${h})`,
    text: `oklch(0.46 0.10 ${h})`,
    soft: `oklch(0.965 0.028 ${h})`,
    softer: `oklch(0.984 0.014 ${h})`,
    line: `oklch(0.85 0.055 ${h})`,
    ring: `oklch(0.60 0.12 ${h})`,
  };
}

/** Inline CSS custom properties to spread onto a node's style. */
export function accentVars(a: Accent): CSSProperties {
  return {
    ["--acc-solid" as string]: a.solid,
    ["--acc-text" as string]: a.text,
    ["--acc-soft" as string]: a.soft,
    ["--acc-softer" as string]: a.softer,
    ["--acc-line" as string]: a.line,
    ["--acc-ring" as string]: a.ring,
  } as CSSProperties;
}
