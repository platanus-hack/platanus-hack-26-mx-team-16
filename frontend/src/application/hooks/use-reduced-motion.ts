"use client";

import * as React from "react";

/**
 * Tracks the user's `prefers-reduced-motion` setting (SSR-safe).
 *
 * M3 Expressive treats motion as a material, but every animation MUST be
 * skippable. Components branch on this to jump straight to the final state
 * instead of animating. The global CSS guard in `globals.css` is the CSS-only
 * safety net; this hook covers JS-driven motion (count-up, RAF, springs).
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
