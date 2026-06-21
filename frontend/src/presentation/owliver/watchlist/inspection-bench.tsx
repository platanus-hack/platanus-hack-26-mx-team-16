/**
 * InspectionBench — the animated, interactive "Banco de inspección" panel for
 * `/watcher` (brought over from the `/watch` hero card, §F4 → §F11). Keeps the
 * Web vs Agéntico split and the A–F "Escala visible", but the scale is now a
 * LIVE gauge: hover / focus / tap a grade chip and an animated SVG needle sweeps
 * to that band while the risk note swaps in. Color comes ONLY from
 * `gradeColorVar` (DESIGN.md "Grade-Is-Data"); all motion respects
 * `prefers-reduced-motion`.
 */
"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";
import { GRADES, gradeColorVar, gradeLabel } from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

/** Display-only threshold copy per grade (07-scoring bands). */
const BAND: Record<Grade, string> = {
  A: "≥ 90",
  B: "≥ 80",
  C: "≥ 70",
  D: "≥ 60",
  E: "≥ 40",
  F: "< 40",
};

/** One-line risk reading per grade — the "what it means" the gauge explains. */
const RISK_NOTE: Record<Grade, string> = {
  A: "Configuración sólida; sin hallazgos relevantes.",
  B: "Buen estado con mejoras menores pendientes.",
  C: "Aprobado, pero con brechas que conviene cerrar.",
  D: "Debilidades visibles que elevan el riesgo.",
  E: "Exposición seria; requiere atención pronto.",
  F: "Riesgo crítico; corrección urgente.",
};

/** Representative score per grade — where the needle rests inside each band. */
const NEEDLE_SCORE: Record<Grade, number> = {
  A: 95,
  B: 85,
  C: 75,
  D: 65,
  E: 50,
  F: 20,
};

/** The 6 colored bands of the gauge, in score order (F→A, low→high). */
const SEGMENTS: { grade: Grade; from: number; to: number }[] = [
  { grade: "F", from: 0, to: 40 },
  { grade: "E", from: 40, to: 60 },
  { grade: "D", from: 60, to: 70 },
  { grade: "C", from: 70, to: 80 },
  { grade: "B", from: 80, to: 90 },
  { grade: "A", from: 90, to: 100 },
];

// Gauge geometry — a 180° arc, score 0 (left) → 100 (right), pathLength=100 so
// each band maps to its score window directly via strokeDasharray.
const CX = 100;
const CY = 100;
const R = 80;
const ARC_PATH = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;
/** Needle rotation for a score: 50 (top) = 0°, 0 = −90°, 100 = +90°. */
const rotationFor = (score: number) => (score - 50) * 1.8;

export type InspectionBenchProps = { className?: string };

export function InspectionBench({ className }: InspectionBenchProps) {
  const reduced = useReducedMotion();
  const [selected, setSelected] = React.useState<Grade>("A");
  const [preview, setPreview] = React.useState<Grade | null>(null);
  const [mounted, setMounted] = React.useState(false);

  // Sweep the needle in from the failing side on first paint (skip if reduced).
  React.useEffect(() => setMounted(true), []);

  const active = preview ?? selected;
  const targetRotation = rotationFor(NEEDLE_SCORE[active]);
  const rotation = mounted || reduced ? targetRotation : rotationFor(NEEDLE_SCORE.F);
  const sweep = reduced
    ? undefined
    : "transform 700ms cubic-bezier(0.05, 0.7, 0.1, 1)";

  return (
    <section
      data-slot="inspection-bench"
      aria-label="Banco de inspección y escala de grados"
      className={cn(
        "rounded-3xl bg-surface-container-low p-5 shadow-[0_8px_18px_rgba(40,30,8,0.10)]",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-outline-variant pb-4">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
            Banco de inspección
          </p>
          <p className="mt-1 text-sm text-on-surface-variant">
            Web, agentes y grado global en una sola lectura.
          </p>
        </div>
        <span
          className={cn(
            "rounded-2xl bg-primary p-3 text-primary-foreground",
            !reduced && "animate-soft-float"
          )}
        >
          <ShieldWeb className="size-5" />
        </span>
      </div>

      {/* Web vs Agéntico split */}
      <div className="mt-5 grid grid-cols-2 gap-4">
        <div className="border-r border-outline-variant pr-4">
          <ShieldWeb className="size-5 text-primary" />
          <p className="mt-3 font-semibold text-foreground">Web</p>
          <p className="mt-1 text-sm text-on-surface-variant">
            TLS, cabeceras, exposición y configuración.
          </p>
        </div>
        <div>
          <AgenticChip className="size-5 text-tertiary" />
          <p className="mt-3 font-semibold text-foreground">Agéntico</p>
          <p className="mt-1 text-sm text-on-surface-variant">
            Prompts, asistentes y widgets de IA embebidos.
          </p>
        </div>
      </div>

      {/* Escala visible — interactive gauge */}
      <div className="mt-5 border-t border-outline-variant pt-4">
        <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
          Escala visible
        </p>

        <svg
          viewBox="0 6 200 102"
          className="mx-auto mt-3 w-full max-w-[260px]"
          role="img"
          aria-label={`Grado ${active}: ${gradeLabel(active)}, umbral ${BAND[active]}`}
        >
          {/* faint full track */}
          <path
            d={ARC_PATH}
            fill="none"
            stroke="var(--outline-variant)"
            strokeWidth={13}
            strokeLinecap="round"
            opacity={0.5}
          />
          {/* colored grade bands (draw/fade in, staggered) */}
          {SEGMENTS.map((seg, i) => {
            const len = seg.to - seg.from;
            const isActive = seg.grade === active;
            const dimmed = active !== seg.grade;
            return (
              <path
                key={seg.grade}
                d={ARC_PATH}
                pathLength={100}
                fill="none"
                stroke={gradeColorVar(seg.grade)}
                strokeWidth={isActive ? 15 : 11}
                strokeLinecap="butt"
                strokeDasharray={`${len} ${100 - len}`}
                strokeDashoffset={-seg.from}
                style={{
                  opacity: mounted || reduced ? (dimmed ? 0.4 : 1) : 0,
                  transition: reduced
                    ? undefined
                    : `opacity 450ms ease ${i * 70}ms, stroke-width 250ms ease`,
                }}
              />
            );
          })}
          {/* needle */}
          <g
            style={{
              transformOrigin: `${CX}px ${CY}px`,
              transform: `rotate(${rotation}deg)`,
              transition: sweep,
            }}
          >
            <line
              x1={CX}
              y1={CY}
              x2={CX}
              y2={CY - (R - 16)}
              stroke={gradeColorVar(active)}
              strokeWidth={3.5}
              strokeLinecap="round"
              style={{ transition: reduced ? undefined : "stroke 300ms ease" }}
            />
            <circle cx={CX} cy={CY - (R - 16)} r={4} fill={gradeColorVar(active)} />
          </g>
          <circle cx={CX} cy={CY} r={7} fill="var(--foreground)" />
          <circle cx={CX} cy={CY} r={3} fill="var(--surface-container-low)" />
        </svg>

        {/* active reading (animated swap) */}
        <div
          className="mt-1 flex items-center justify-center gap-3 text-center"
          aria-live="polite"
        >
          <span
            key={active}
            className={cn(
              "inline-flex size-10 items-center justify-center rounded-xl font-mono text-lg font-bold text-[color:#171105]",
              !reduced && "animate-m3-enter"
            )}
            style={{ backgroundColor: gradeColorVar(active) }}
          >
            {active}
          </span>
          <p className="text-left">
            <span className="text-sm font-semibold text-foreground">
              {gradeLabel(active)}{" "}
              <span className="font-mono font-normal text-on-surface-variant">
                {BAND[active]}
              </span>
            </span>
            <br />
            <span className="text-xs text-on-surface-variant">
              {RISK_NOTE[active]}
            </span>
          </p>
        </div>

        {/* interactive chips */}
        <div className="mt-4 flex flex-wrap justify-center gap-1.5">
          {GRADES.map((g) => (
            <button
              key={g}
              type="button"
              onPointerEnter={() => setPreview(g)}
              onPointerLeave={() => setPreview(null)}
              onFocus={() => setPreview(g)}
              onBlur={() => setPreview(null)}
              onClick={() => setSelected(g)}
              aria-pressed={selected === g}
              aria-label={`${gradeLabel(g)} — ${BAND[g]}`}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-1 outline-none transition-all focus-visible:ring-2 focus-visible:ring-ring",
                active === g
                  ? "border-outline bg-card shadow-xs"
                  : "border-transparent hover:bg-card"
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "inline-flex size-5 items-center justify-center rounded-md font-mono text-[11px] font-bold text-[color:#171105] transition-transform",
                  active === g && "scale-110"
                )}
                style={{ backgroundColor: gradeColorVar(g) }}
              >
                {g}
              </span>
              <span className="text-xs text-on-surface-variant">{gradeLabel(g)}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
