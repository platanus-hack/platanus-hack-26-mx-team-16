"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/src/application/lib/utils";
import { WorkflowProcessingJobStatus } from "@/src/domain/events/processing-job-event";

interface ProcessingJobStatusBadgeProps {
  status: WorkflowProcessingJobStatus;
  /** 0-100. Shown only while the set is in a transient state. */
  progressPct?: number;
  /** Current pipeline step copy, e.g. "Extrayendo texto…". */
  stepLabel?: string | null;
  className?: string;
}

const TERMINAL_PRESET: Partial<
  Record<
    WorkflowProcessingJobStatus,
    { label: string; icon: string; pill: string }
  >
> = {
  [WorkflowProcessingJobStatus.COMPLETED]: {
    label: "Completado",
    icon: "✓",
    pill: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  },
  [WorkflowProcessingJobStatus.PARTIAL]: {
    label: "Parcial",
    icon: "◐",
    pill: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  },
  [WorkflowProcessingJobStatus.FAILED]: {
    label: "FALLIDO",
    icon: "✕",
    pill: "bg-destructive/10 text-destructive",
  },
};

const TRANSIENT_DEFAULT_LABEL: Partial<
  Record<WorkflowProcessingJobStatus, string>
> = {
  [WorkflowProcessingJobStatus.PENDING]: "En cola",
  [WorkflowProcessingJobStatus.RUNNING]: "Iniciando…",
  [WorkflowProcessingJobStatus.PROCESSING]: "Procesando…",
};

/**
 * Maps raw `JobStep` values emitted by the Temporal pipeline to
 * Spanish copy fit for end users. Keys match the values in
 * `src/domain/events/processing-job-event.ts:JobStep`.
 */
const STEP_LABEL: Record<string, string> = {
  extract_text: "Leyendo…",
  classify_pages: "Clasificando…",
  persist_documents: "Guardando…",
  extract_fields: "Extrayendo…",
  validate_extraction: "Validando…",
};

function humanizeStepLabel(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return STEP_LABEL[trimmed] ?? trimmed;
}

// 5 pipeline steps (extract_text, classify, persist, extract_fields, validate)
// → 4 internal boundaries used as faint tick marks inside the track.
const STEP_TICKS = [20, 40, 60, 80];

export function ProcessingJobStatusBadge({
  status,
  progressPct,
  stepLabel,
  className,
}: ProcessingJobStatusBadgeProps) {
  const terminal = TERMINAL_PRESET[status];
  if (terminal) {
    return (
      <span
        className={cn(
          "flex h-[26px] w-full min-w-[88px] items-center justify-center gap-1.5 rounded-full px-3",
          "font-mono text-[10px] uppercase tracking-[0.18em]",
          terminal.pill,
          className,
        )}
      >
        <span aria-hidden className="text-[11px] leading-none">
          {terminal.icon}
        </span>
        {terminal.label}
      </span>
    );
  }

  const rawPct = typeof progressPct === "number" ? progressPct : 0;
  const fillPct = Math.min(100, Math.max(4, rawPct));
  const roundedPct = Math.round(rawPct);
  const label =
    humanizeStepLabel(stepLabel) ||
    TRANSIENT_DEFAULT_LABEL[status] ||
    "Procesando…";

  return (
    <div
      role="progressbar"
      aria-valuenow={roundedPct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn(
        "relative isolate flex h-[26px] w-full min-w-[88px] items-center overflow-hidden rounded-full",
        "border border-border/60 bg-muted/40",
        className,
      )}
    >
      {/* Filled zone (base tint) */}
      <div
        className="absolute inset-y-0 left-0 bg-primary/15 transition-[width] duration-500 ease-out"
        style={{ width: `${fillPct}%` }}
        aria-hidden
      />
      {/* Soft wave at the leading edge — blurred gradient that gives a "liquid front" feel */}
      <div
        className="pointer-events-none absolute inset-y-0 w-8 bg-gradient-to-r from-transparent via-primary/25 to-primary/40 blur-[1px] transition-[transform] duration-500 ease-out"
        style={{ transform: `translateX(calc(${fillPct}% - 2rem))` }}
        aria-hidden
      />
      {/* Step boundary ticks — faint vertical hairlines */}
      {STEP_TICKS.map((tick) => (
        <span
          key={tick}
          className="pointer-events-none absolute inset-y-1 w-px bg-foreground/10"
          style={{ left: `${tick}%` }}
          aria-hidden
        />
      ))}
      {/* Ambient shimmer — keeps the bar visibly alive even when % hasn't advanced */}
      <div
        className="pointer-events-none absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-foreground/10 to-transparent motion-reduce:hidden"
        style={{ animation: "shimmer 2.4s ease-in-out infinite" }}
        aria-hidden
      />
      {/* Layer 1: muted label, visible across the full track */}
      <div className="relative z-10 flex w-full items-center gap-1.5 px-3 text-muted-foreground">
        <Loader2
          className="h-3 w-3 shrink-0 motion-safe:animate-spin motion-reduce:opacity-60"
          style={{ animationDuration: "1.6s" }}
          aria-hidden
        />
        <span className="truncate text-[11px] font-medium">{label}</span>
        <span className="ml-auto text-[10px] font-medium tabular-nums">
          {roundedPct}%
        </span>
      </div>
      {/* Layer 2: strong label, clipped to the fill zone — produces a real */}
      {/* contrast flip at the fill boundary without mix-blend hacks. */}
      <div
        className="pointer-events-none absolute inset-0 z-20 flex items-center gap-1.5 px-3 text-foreground"
        style={{ clipPath: `inset(0 ${100 - fillPct}% 0 0)` }}
        aria-hidden
      >
        <Loader2
          className="h-3 w-3 shrink-0 motion-safe:animate-spin motion-reduce:opacity-60"
          style={{ animationDuration: "1.6s" }}
        />
        <span className="truncate text-[11px] font-medium">{label}</span>
        <span className="ml-auto text-[10px] font-medium tabular-nums">
          {roundedPct}%
        </span>
      </div>
    </div>
  );
}
