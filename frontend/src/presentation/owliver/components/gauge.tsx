/**
 * Gauge — semicircular sub-score dial (Web / Agéntico, §F7/§F9), built on
 * **recharts** `RadialBarChart` (the charting library DESIGN.md specifies). A
 * 180°→0° half-gauge: a tonal track plus a value arc in the grade-ramp color
 * with rounded caps. The score counts up (rAF, `emphasized-decelerate`) and the
 * recharts bar tracks the same animated value, so number and arc stay in sync.
 *
 * Honors reduced-motion (no count-up/sweep). The grade is taken from the server
 * value when provided, else derived from the score band (`gradeFromScore`).
 */
"use client";

import * as React from "react";
import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";

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
  /** Optional leading glyph (icon node). */
  icon?: React.ReactNode;
  size?: number;
  className?: string;
  /** Shown instead of the score when null (e.g. "sin auditar"). */
  emptyHint?: string;
};

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

  const effectiveGrade: Grade | null =
    grade ?? (hasScore ? gradeFromScore(target) : null);
  const color = effectiveGrade ? gradeColorVar(effectiveGrade) : "var(--outline)";

  // Geometry: a half-gauge anchored at the bottom of the chart box.
  const stroke = Math.max(8, Math.round(size * 0.092));
  const chartHeight = Math.round(size / 2 + stroke / 2 + 8);
  const outer = size / 2 - 2;
  const inner = outer - stroke;

  const display = Math.round(animated);

  return (
    <div
      data-slot="gauge"
      className={cn("inline-flex flex-col items-center", className)}
    >
      <div
        className="relative"
        style={{ width: size, height: chartHeight }}
        role="img"
        aria-label={`${label ?? "Score"}: ${
          hasScore ? display : emptyHint
        }${effectiveGrade ? `, grado ${effectiveGrade}` : ""}`}
      >
        <RadialBarChart
          width={size}
          height={chartHeight}
          cx={size / 2}
          cy={chartHeight - 2}
          innerRadius={inner}
          outerRadius={outer}
          barSize={stroke}
          startAngle={180}
          endAngle={0}
          margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          data={[{ value: hasScore ? animated : 0 }]}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background={{ fill: "var(--surface-container-highest)" }}
            dataKey="value"
            angleAxisId={0}
            cornerRadius={stroke / 2}
            fill={color}
            isAnimationActive={false}
          />
        </RadialBarChart>

        {/* Center readout — score + grade stacked in the clear dome interior. */}
        <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
          <span
            className="font-mono font-semibold tabular-nums leading-none text-foreground"
            style={{ fontSize: size * 0.2 }}
          >
            {hasScore ? display : "—"}
          </span>
          {effectiveGrade && (
            <span
              className="font-mono font-bold leading-none"
              style={{
                fontSize: size * 0.135,
                marginTop: size * 0.03,
                marginBottom: size * 0.04,
                color,
              }}
            >
              {effectiveGrade}
            </span>
          )}
        </div>
      </div>

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
