/**
 * DimensionMeter — the leaderboard's double "🛡️ Web vs 🤖 Agéntico" mini-gauge
 * (§F4). The contrast between the two sub-scores IS the differentiator (the star
 * SAT row reads "C web / F agéntico"), so each dimension renders a compact bar
 * tinted by its own per-dimension grade off the A–F ramp — never a hardcoded hex.
 *
 * When a dimension has no score (e.g. agentic `detected_not_tested` /
 * `no_surface`) we render a muted "—" so the row never implies a clean pass.
 */
import type { ReactNode } from "react";

import { cn } from "@/src/application/lib/utils";
import {
  gradeColorVar,
  gradeFromScore,
} from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

type DimensionMeterRowProps = {
  /** Dimension icon + a11y label. */
  icon: ReactNode;
  label: string;
  score: number | null | undefined;
  /** Authoritative per-dimension letter (display only fallback to bands). */
  grade?: Grade | null;
};

function MeterRow({ icon, label, score, grade }: DimensionMeterRowProps) {
  const hasScore = typeof score === "number";
  const letter: Grade | null = hasScore
    ? (grade ?? gradeFromScore(score))
    : (grade ?? null);
  const color = letter ? gradeColorVar(letter) : "var(--outline)";

  return (
    <div className="flex items-center gap-2" aria-label={`${label}: ${hasScore ? score : "sin datos"}`}>
      <span className="flex leading-none">{icon}</span>
      <div
        className="relative h-1.5 w-12 overflow-hidden rounded-full bg-surface-container-high"
        aria-hidden
      >
        {hasScore ? (
          <span
            className="absolute inset-y-0 left-0 rounded-full"
            style={{ width: `${Math.max(4, score)}%`, backgroundColor: color }}
          />
        ) : null}
      </div>
      <span
        className="w-7 text-right font-mono text-xs tabular-nums"
        style={{ color: hasScore ? color : "var(--on-surface-variant)" }}
      >
        {hasScore ? score : "—"}
      </span>
    </div>
  );
}

export type DimensionMeterProps = {
  webScore: number | null | undefined;
  agenticScore: number | null | undefined;
  webGrade?: Grade | null;
  agenticGrade?: Grade | null;
  className?: string;
};

/** Stacked 🛡️/🤖 mini-gauges for a leaderboard row. */
export function DimensionMeter({
  webScore,
  agenticScore,
  webGrade,
  agenticGrade,
  className,
}: DimensionMeterProps) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <MeterRow
        icon={<ShieldWeb className="size-3.5 text-primary" />}
        label="Web"
        score={webScore}
        grade={webGrade}
      />
      <MeterRow
        icon={<AgenticChip className="size-3.5 text-tertiary" />}
        label="Agéntico"
        score={agenticScore}
        grade={agenticGrade}
      />
    </div>
  );
}
