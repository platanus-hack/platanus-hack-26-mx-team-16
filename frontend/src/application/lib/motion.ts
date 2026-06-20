/**
 * Material 3 Expressive motion tokens (Owliver).
 *
 * Mirrors the values in `/DESIGN.md` and the CSS custom properties in
 * `globals.css` (`--ease-*`, `--dur-*`). Use these from JS (Web Animations,
 * inline styles, `CountUp`) or feed `spring` into a physics lib (Framer
 * Motion / react-spring) if/when one is added.
 */

/** Durations in milliseconds. */
export const duration = {
  short1: 50,
  short2: 100,
  short3: 150,
  short4: 200,
  medium1: 250,
  medium2: 300,
  medium3: 350,
  medium4: 400,
  long1: 450,
  long2: 500,
  long3: 550,
  long4: 600,
  extraLong: 700,
} as const;

/** CSS easing strings. */
export const easing = {
  emphasized: "cubic-bezier(0.2, 0, 0, 1)",
  emphasizedDecelerate: "cubic-bezier(0.05, 0.7, 0.1, 1)",
  emphasizedAccelerate: "cubic-bezier(0.3, 0, 0.8, 0.15)",
  standard: "cubic-bezier(0.2, 0, 0, 1)",
} as const;

/** Easing as JS functions (for RAF-driven motion like count-up). */
export const easeFn = {
  emphasizedDecelerate: (t: number) => 1 - Math.pow(1 - t, 3),
  emphasizedAccelerate: (t: number) => t * t * t,
  standard: (t: number) =>
    t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
} as const;

/** Physical spring presets (stiffness / damping ratio) for a spring lib. */
export const spring = {
  spatialFast: { stiffness: 800, damping: 0.85 },
  spatialDefault: { stiffness: 380, damping: 0.8 },
  spatialSlow: { stiffness: 200, damping: 0.8 },
  effectsDefault: { stiffness: 1600, damping: 1 },
} as const;
