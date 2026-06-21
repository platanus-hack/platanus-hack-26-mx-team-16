/**
 * Scan lifecycle status — the NON-grade states a run can be in (queued, running,
 * failed, cancelled). Kept deliberately OFF the A–F ramp (DESIGN.md
 * "Grade-Is-Data Rule"): a grade is the outcome, a status is where the run is.
 * Violet = activity, vermilion = failure, neutral = waiting.
 *
 * `done` / `partial` runs render their GradeBadge instead, so this only speaks
 * for the states without an authoritative grade.
 */
import { CircleDashed, Clock, Loader2, OctagonAlert, Square } from "lucide-react";
import type { ComponentType } from "react";

import { cn } from "@/src/application/lib/utils";
import type { ScanStatus } from "@/src/application/owliver/schemas/api";

type StatusVisual = {
  label: string;
  Icon: ComponentType<{ className?: string }>;
  /** Text/border tint token. */
  tint: string;
  /** Soft fill token. */
  fill: string;
  /** Spin / pulse the icon (running only). */
  live?: boolean;
};

export const SCAN_STATUS_META: Record<ScanStatus, StatusVisual> = {
  queued: {
    label: "En cola",
    Icon: Clock,
    tint: "text-on-surface-variant",
    fill: "bg-surface-container-high",
  },
  running: {
    label: "En curso",
    Icon: Loader2,
    tint: "text-primary",
    fill: "bg-primary-container",
    live: true,
  },
  done: {
    label: "Completo",
    Icon: Square,
    tint: "text-secondary",
    fill: "bg-secondary-container",
  },
  partial: {
    label: "Parcial",
    Icon: CircleDashed,
    tint: "text-on-surface-variant",
    fill: "bg-surface-container-high",
  },
  failed: {
    label: "Falló",
    Icon: OctagonAlert,
    tint: "text-destructive",
    fill: "bg-destructive/10",
  },
  cancelled: {
    label: "Cancelado",
    Icon: Square,
    tint: "text-on-surface-variant",
    fill: "bg-surface-container-high",
  },
};

/** Inline status pill (icon + label) for the row meta line and the empty/filter UI. */
export function ScanStatusPill({
  status,
  className,
}: {
  status: ScanStatus;
  className?: string;
}) {
  const { label, Icon, tint, live } = SCAN_STATUS_META[status];
  return (
    <span
      data-slot="scan-status-pill"
      data-status={status}
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-full border border-current/25 bg-current/10 px-2 text-[11px] font-medium whitespace-nowrap",
        tint,
        className
      )}
    >
      <Icon
        className={cn("size-3", live && "motion-safe:animate-spin")}
        aria-hidden
      />
      {label}
    </span>
  );
}

/**
 * The square status glyph that stands in for the GradeBadge on the left of a row
 * that has no grade yet. Same footprint as `GradeBadge size="md"` so every row
 * keeps a single vertical rhythm. Running shows live progress as a ring fill.
 */
export function ScanStatusGlyph({
  status,
  progress,
  className,
}: {
  status: ScanStatus;
  progress?: number;
  className?: string;
}) {
  const { Icon, tint, fill, live } = SCAN_STATUS_META[status];
  return (
    <span
      data-slot="scan-status-glyph"
      data-status={status}
      aria-hidden
      className={cn(
        "relative inline-flex h-10 min-w-10 items-center justify-center rounded-xl",
        fill,
        tint,
        className
      )}
    >
      <Icon className={cn("size-5", live && "motion-safe:animate-spin")} />
      {status === "running" && typeof progress === "number" ? (
        <span className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 rounded-full bg-primary px-1 font-mono text-[9px] font-semibold leading-tight text-primary-foreground tabular-nums">
          {Math.round(progress)}
        </span>
      ) : null}
    </span>
  );
}
