/**
 * ProgressBar — the scan's live progress (§F6 header), wrapping the existing M3
 * Expressive `WavyProgress` (the squiggly active indicator). Adds the readable
 * `current_phase` label, the 0–100 percentage (mono = measured value), and an
 * optional elapsed timer with a reassuring "< 90s" cap.
 *
 * Pure presentational — the theater feeds it `progress` / `currentPhase` from the
 * store. Works in the SOC theater (inherits `--primary` from the scoped `.soc`
 * palette, so the wave goes cyan there automatically).
 */
"use client";

import { cn } from "@/src/application/lib/utils";
import { WavyProgress } from "@/src/presentation/components/common/wavy-progress";

export type ProgressBarProps = {
  /** 0–100. */
  value: number;
  /** Readable phase, e.g. "Sondeando chatbot…". */
  phase?: string | null;
  /** Elapsed seconds (optional timer). */
  elapsedSeconds?: number | null;
  /** Reassuring cap shown next to the timer (default 90). */
  budgetSeconds?: number;
  className?: string;
  height?: number;
};

function fmt(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export function ProgressBar({
  value,
  phase,
  elapsedSeconds,
  budgetSeconds = 90,
  className,
  height = 12,
}: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div data-slot="progress-bar" className={cn("w-full", className)}>
      <div className="mb-2 flex items-end justify-between gap-3">
        <span className="truncate text-sm font-medium text-on-surface-variant">
          {phase ?? "Preparando…"}
        </span>
        <span className="flex shrink-0 items-baseline gap-2 font-mono text-sm tabular-nums">
          {typeof elapsedSeconds === "number" && (
            <span className="text-on-surface-variant">
              {fmt(elapsedSeconds)}
              <span className="opacity-60"> / &lt;{fmt(budgetSeconds)}</span>
            </span>
          )}
          <span className="font-semibold text-foreground">{Math.round(pct)}%</span>
        </span>
      </div>
      <WavyProgress value={pct} height={height} />
    </div>
  );
}
