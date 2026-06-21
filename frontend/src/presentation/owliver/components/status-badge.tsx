/**
 * StatusBadge — the two coverage badges Owliver shows next to grades:
 *  - "IA detectada, sin auditar"  → agenticStatus === "detected_not_tested"
 *  - "cobertura parcial"          → partial coverage (grade capped at C)
 *
 * Plus convenience helpers to derive the badges from a scan/ranking row so every
 * screen renders them identically. Never shown as "sin riesgo".
 */
import { EyeOff, ShieldOff } from "lucide-react";

import { cn } from "@/src/application/lib/utils";
import type { AgenticStatus } from "@/src/application/owliver/schemas/api";

export type StatusBadgeVariant = "detected-not-tested" | "partial-coverage";

const COPY: Record<
  StatusBadgeVariant,
  { label: string; icon: typeof EyeOff }
> = {
  "detected-not-tested": { label: "IA detectada, sin auditar", icon: EyeOff },
  "partial-coverage": { label: "Cobertura parcial", icon: ShieldOff },
};

export type StatusBadgeProps = {
  variant: StatusBadgeVariant;
  className?: string;
};

export function StatusBadge({ variant, className }: StatusBadgeProps) {
  const { label, icon: Icon } = COPY[variant];
  return (
    <span
      data-slot="status-badge"
      data-variant={variant}
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-full border border-outline-variant bg-surface-container px-2 text-[11px] font-medium text-on-surface-variant whitespace-nowrap",
        className
      )}
    >
      <Icon className="size-3" aria-hidden />
      {label}
    </span>
  );
}

/**
 * Render the coverage badges that apply to a row/scan. Use everywhere a grade
 * appears so the rules (§F4/§F7) are consistent.
 */
export function CoverageBadges({
  agenticStatus,
  partialCoverage,
  className,
}: {
  agenticStatus: AgenticStatus;
  partialCoverage?: boolean;
  className?: string;
}) {
  const badges: StatusBadgeVariant[] = [];
  if (agenticStatus === "detected_not_tested")
    badges.push("detected-not-tested");
  if (partialCoverage) badges.push("partial-coverage");
  if (badges.length === 0) return null;
  return (
    <span className={cn("inline-flex flex-wrap gap-1", className)}>
      {badges.map((v) => (
        <StatusBadge key={v} variant={v} />
      ))}
    </span>
  );
}
