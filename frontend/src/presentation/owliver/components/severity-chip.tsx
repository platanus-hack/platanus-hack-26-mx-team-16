/**
 * SeverityChip — critical/high/medium/low/info with an ICON + TEXT (never color
 * alone, §F12 a11y). Color maps onto the grade ramp via `severityColorVar`.
 * Mono label = "this is a measured value".
 */
import {
  AlertOctagon,
  AlertTriangle,
  Info,
  ShieldAlert,
  ShieldQuestion,
} from "lucide-react";
import type { ComponentType } from "react";

import { cn } from "@/src/application/lib/utils";
import {
  severityColorVar,
  severityLabel,
} from "@/src/application/owliver/lib/grade";
import type { Severity } from "@/src/application/owliver/schemas/api";

const ICONS: Record<Severity, ComponentType<{ className?: string }>> = {
  critical: AlertOctagon,
  high: ShieldAlert,
  medium: AlertTriangle,
  low: ShieldQuestion,
  info: Info,
};

export type SeverityChipProps = {
  severity: Severity;
  className?: string;
  /** Hide the text label (icon + tooltip only). Keeps an sr-only label. */
  iconOnly?: boolean;
  size?: "sm" | "md";
};

export function SeverityChip({
  severity,
  className,
  iconOnly = false,
  size = "md",
}: SeverityChipProps) {
  const Icon = ICONS[severity];
  const color = severityColorVar(severity);
  const label = severityLabel(severity);

  return (
    <span
      data-slot="severity-chip"
      data-severity={severity}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-mono font-medium whitespace-nowrap",
        size === "sm" ? "h-6 px-2 text-[11px]" : "h-7 px-2.5 text-xs",
        className
      )}
      style={{
        color,
        borderColor: `color-mix(in oklab, ${color} 40%, transparent)`,
        backgroundColor: `color-mix(in oklab, ${color} 12%, transparent)`,
      }}
      title={label}
    >
      <Icon className={size === "sm" ? "size-3" : "size-3.5"} aria-hidden />
      {iconOnly ? <span className="sr-only">{label}</span> : label}
    </span>
  );
}
