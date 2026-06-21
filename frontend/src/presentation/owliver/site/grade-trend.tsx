/**
 * GradeTrend — a dependency-free SVG line chart of the overall grade over time
 * (§F9). recharts is NOT a dependency, so this is hand-rolled SVG (mirrors the
 * Gauge approach): the y-axis is the A–F band (A on top, F at the bottom) and
 * each point is colored by its grade via `gradeColorVar` — the single source of
 * state color. Honors reduced-motion (the draw-in is purely a CSS transition the
 * component renders statically when motion is reduced).
 *
 * Grades are server values; we NEVER recompute them. We only map the letter to a
 * vertical position (A=0 … F=5) for plotting.
 */
"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";
import { GRADES, gradeColorVar } from "@/src/application/owliver/lib/grade";
import type { ScanHistoryEntry } from "@/src/application/owliver/schemas/api";

export type GradeTrendProps = {
  history: ScanHistoryEntry[];
  className?: string;
  height?: number;
};

const PAD_X = 28;
const PAD_TOP = 14;
const PAD_BOTTOM = 26;

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
  });
}

export function GradeTrend({ history, className, height = 180 }: GradeTrendProps) {
  const reduced = useReducedMotion();
  const [drawn, setDrawn] = React.useState(reduced);

  React.useEffect(() => {
    if (reduced) {
      setDrawn(true);
      return;
    }
    const raf = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(raf);
  }, [reduced]);

  if (history.length === 0) return null;

  // Single-point histories still render a labelled dot.
  const width = 560;
  const innerW = width - PAD_X * 2;
  const innerH = height - PAD_TOP - PAD_BOTTOM;
  const rows = GRADES.length - 1; // 5 gaps between A..F

  const xFor = (i: number) =>
    history.length === 1
      ? width / 2
      : PAD_X + (innerW * i) / (history.length - 1);
  const yFor = (gradeIndex: number) =>
    PAD_TOP + (innerH * gradeIndex) / rows;

  const points = history.map((h, i) => ({
    x: xFor(i),
    y: yFor(GRADES.indexOf(h.overallGrade)),
    entry: h,
  }));

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label="Tendencia del grado a lo largo del tiempo"
        style={{ minWidth: 320 }}
      >
        {/* Grade band gridlines + axis letters */}
        {GRADES.map((g, gi) => {
          const y = yFor(gi);
          return (
            <g key={g}>
              <line
                x1={PAD_X}
                x2={width - PAD_X}
                y1={y}
                y2={y}
                stroke="var(--outline-variant)"
                strokeWidth={1}
                strokeDasharray="2 4"
                opacity={0.6}
              />
              <text
                x={PAD_X - 10}
                y={y + 4}
                textAnchor="end"
                className="font-mono"
                style={{ fontSize: 11, fill: gradeColorVar(g), fontWeight: 700 }}
              >
                {g}
              </text>
            </g>
          );
        })}

        {/* Trend line */}
        {points.length > 1 && (
          <path
            d={linePath}
            fill="none"
            stroke="var(--primary)"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              transition: reduced ? undefined : "stroke-dashoffset 900ms ease",
              strokeDasharray: 1200,
              strokeDashoffset: drawn ? 0 : 1200,
            }}
          />
        )}

        {/* Points + date labels */}
        {points.map((p) => (
          <g key={p.entry.scanId}>
            <circle
              cx={p.x}
              cy={p.y}
              r={5}
              fill={gradeColorVar(p.entry.overallGrade)}
              stroke="var(--card)"
              strokeWidth={2}
            />
            <text
              x={p.x}
              y={height - 8}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 10, fill: "var(--on-surface-variant)" }}
            >
              {shortDate(p.entry.scannedAt)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
