"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";

type WavyProgressProps = {
  /** Progress 0–100. */
  value: number;
  className?: string;
  /** Bar height in px (default 12). */
  height?: number;
};

/**
 * Material 3 Expressive **wavy** linear progress. The active portion is a
 * squiggly line that travels while running and flattens to a straight line on
 * complete (or when reduced-motion is on); the remaining track is a flat
 * rounded line. Dependency-free SVG.
 */
export function WavyProgress({
  value,
  className,
  height = 12,
}: WavyProgressProps) {
  const reduced = useReducedMotion();
  const pct = Math.max(0, Math.min(100, value));
  const done = pct >= 100;
  const flat = done || reduced;

  const mid = height / 2;
  const amp = flat ? 0 : Math.min(3, mid - 2);
  const wavelength = 16;
  const vbWidth = 2000;

  // Build a repeating smooth wave across the viewBox.
  let d = `M0 ${mid}`;
  const half = wavelength / 2;
  const q = wavelength / 4;
  for (let x = 0; x <= vbWidth; x += wavelength) {
    d += ` q ${q} ${-amp} ${half} 0 q ${q} ${amp} ${half} 0`;
  }

  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("relative w-full overflow-hidden", className)}
      style={{ height }}
    >
      {/* Track (remaining) */}
      <div
        className="absolute inset-x-0 rounded-full bg-surface-container-highest"
        style={{ top: mid - 1.5, height: 3 }}
      />
      {/* Active wavy fill, clipped to pct width */}
      <div
        className="absolute inset-y-0 left-0 overflow-hidden"
        style={{ width: `${pct}%` }}
      >
        <svg
          width={vbWidth}
          height={height}
          viewBox={`0 0 ${vbWidth} ${height}`}
          fill="none"
          className={cn("block h-full", !flat && "animate-wavy")}
          style={{ width: vbWidth }}
          aria-hidden
        >
          <path
            d={d}
            stroke="var(--primary)"
            strokeWidth={3}
            strokeLinecap="round"
          />
        </svg>
      </div>
    </div>
  );
}
