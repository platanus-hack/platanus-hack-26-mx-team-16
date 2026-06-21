/**
 * Gauge — semicircular sub-score dial (🛡️ Web / 🤖 Agéntico, §F7/§F9).
 * Dependency-free SVG (no recharts): a 180° arc that sweeps 0→value on
 * `emphasized-decelerate`, with a center score + grade letter in Roboto Mono.
 *
 * The arc color is the grade ramp (`gradeColorVar`). Honors reduced-motion (no
 * sweep). The grade is rendered from the server value when provided; otherwise a
 * display-only band is derived (`gradeFromScore`).
 */
"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { duration, easeFn } from "@/src/application/lib/motion";
import { cn } from "@/src/application/lib/utils";
import {
  gradeColorVar,
  gradeFromScore,
} from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";

export type GaugeProps = {
  /** 0..100 sub-score, or null when not yet scored. */
  score: number | null | undefined;
  /** Server grade for this dimension; derived from score if omitted. */
  grade?: Grade | null;
  /** Dimension label, e.g. "Web" / "Agéntico". */
  label?: string;
  /** Optional leading glyph (emoji/icon node). */
  icon?: React.ReactNode;
  size?: number;
  className?: string;
  /** Shown instead of the score when null (e.g. "sin auditar"). */
  emptyHint?: string;
};

const STROKE = 12;

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Semicircle arc path from 180° (left) sweeping `frac` toward 0° (right). */
function arcPath(cx: number, cy: number, r: number, frac: number) {
  const start = polar(cx, cy, r, 180);
  const endDeg = 180 - 180 * Math.max(0, Math.min(1, frac));
  const end = polar(cx, cy, r, endDeg);
  const largeArc = 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export function Gauge({
  score,
  grade,
  label,
  icon,
  size = 160,
  className,
  emptyHint = "sin datos",
}: GaugeProps) {
  const reduced = useReducedMotion();
  const hasScore = typeof score === "number";
  const target = hasScore ? Math.max(0, Math.min(100, score)) : 0;
  const [animated, setAnimated] = React.useState(reduced ? target : 0);

  React.useEffect(() => {
    if (reduced || !hasScore) {
      setAnimated(target);
      return;
    }
    let raf = 0;
    let start: number | null = null;
    const tick = (ts: number) => {
      if (start === null) start = ts;
      const t = Math.min(1, (ts - start) / duration.extraLong);
      setAnimated(target * easeFn.emphasizedDecelerate(t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced, hasScore]);

  const cx = size / 2;
  const r = (size - STROKE) / 2;
  const cy = r + STROKE / 2;
  const height = cy + STROKE / 2 + 4;

  const effectiveGrade: Grade | null =
    grade ?? (hasScore ? gradeFromScore(target) : null);
  const color = effectiveGrade ? gradeColorVar(effectiveGrade) : "var(--outline)";

  return (
    <div
      data-slot="gauge"
      className={cn("inline-flex flex-col items-center", className)}
    >
      <svg
        width={size}
        height={height}
        viewBox={`0 0 ${size} ${height}`}
        role="img"
        aria-label={`${label ?? "Score"}: ${hasScore ? Math.round(target) : emptyHint}${effectiveGrade ? `, grado ${effectiveGrade}` : ""}`}
      >
        {/* Track */}
        <path
          d={arcPath(cx, cy, r, 1)}
          fill="none"
          stroke="var(--surface-container-highest)"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />
        {/* Value */}
        {hasScore && (
          <path
            d={arcPath(cx, cy, r, animated / 100)}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        )}
        {/* Center readout — score + grade stacked INSIDE the arc. Both must
           stay above the baseline (cy); placing the grade below it pushed the
           glyph past the SVG bottom edge and clipped it. */}
        <text
          x={cx}
          y={cy - size * (effectiveGrade ? 0.17 : 0.08)}
          textAnchor="middle"
          className="font-mono tabular-nums"
          style={{ fontSize: size * 0.2, fontWeight: 600, fill: "var(--foreground)" }}
        >
          {hasScore ? Math.round(animated) : "—"}
        </text>
        {effectiveGrade && (
          <text
            x={cx}
            y={cy - size * 0.02}
            textAnchor="middle"
            className="font-mono"
            style={{ fontSize: size * 0.14, fontWeight: 700, fill: color }}
          >
            {effectiveGrade}
          </text>
        )}
      </svg>
      {label && (
        <div className="mt-1 flex items-center gap-1.5 text-sm font-medium text-on-surface-variant">
          {icon}
          <span>{label}</span>
        </div>
      )}
      {!hasScore && (
        <span className="text-xs text-on-surface-variant">{emptyHint}</span>
      )}
    </div>
  );
}
