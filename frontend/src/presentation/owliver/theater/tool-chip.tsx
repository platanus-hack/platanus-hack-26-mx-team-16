/**
 * ToolChip (SOC theater, §F6) — a scanner tool's live status pill with a status
 * dot. Maps `ToolRunState` (from the theater store) to a color + motion:
 *   - idle    → dim, dot quiet.
 *   - running → amber (`--tertiary`/owl-tool), dot pulses.
 *   - ok      → green (`--success`), dot solid.
 *   - failed  → red (`--destructive`), dot solid (also covers timeout).
 *
 * Mono label (the tool name reads as telemetry). Designed for the dark SOC
 * palette but uses theme tokens so it also renders correctly on light surfaces.
 * Reduced-motion drops the pulse.
 */
"use client";

import { cn } from "@/src/application/lib/utils";
import type { ToolRunState } from "@/src/application/owliver/stores/theater-store";

export type ToolChipProps = {
  tool: string;
  state: ToolRunState;
  className?: string;
};

const STATE_STYLE: Record<
  ToolRunState,
  { dot: string; text: string; ring: string; pulse: boolean; label: string }
> = {
  idle: {
    dot: "var(--outline)",
    text: "var(--muted-foreground)",
    ring: "var(--outline-variant)",
    pulse: false,
    label: "en espera",
  },
  running: {
    dot: "var(--tertiary)",
    text: "var(--on-tertiary-container, var(--tertiary))",
    ring: "var(--tertiary)",
    pulse: true,
    label: "corriendo",
  },
  ok: {
    dot: "var(--success)",
    text: "var(--success-deep, var(--success))",
    ring: "var(--success)",
    pulse: false,
    label: "ok",
  },
  failed: {
    dot: "var(--destructive)",
    text: "var(--destructive-deep, var(--destructive))",
    ring: "var(--destructive)",
    pulse: false,
    label: "falló",
  },
};

export function ToolChip({ tool, state, className }: ToolChipProps) {
  const s = STATE_STYLE[state];
  return (
    <span
      data-slot="tool-chip"
      data-tool={tool}
      data-state={state}
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 font-mono text-[11px] font-medium whitespace-nowrap transition-colors",
        className
      )}
      style={{
        color: s.text,
        borderColor: `color-mix(in oklab, ${s.ring} 45%, transparent)`,
        backgroundColor: `color-mix(in oklab, ${s.dot} 12%, transparent)`,
      }}
      title={`${tool} — ${s.label}`}
    >
      <span
        aria-hidden
        className={cn(
          "size-2 rounded-full",
          state === "running" && "motion-safe:animate-pulse"
        )}
        style={{ backgroundColor: s.dot }}
      />
      <span>{tool}</span>
      <span className="sr-only"> — {s.label}</span>
    </span>
  );
}
