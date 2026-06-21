/**
 * TrendIndicator — ▲▼ vs the previous scan (§F4, display only). "down" means the
 * grade got WORSE (more penalty) so it reads red; "up" reads green; "flat" is a
 * quiet dash. Color is purely directional feedback, kept off the A–F state ramp
 * so it never competes with the grade chip.
 */
import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import { cn } from "@/src/application/lib/utils";

export type Trend = "up" | "down" | "flat";

const MAP: Record<
  Trend,
  { icon: typeof Minus; label: string; className: string }
> = {
  up: { icon: TrendingUp, label: "mejoró vs. escaneo previo", className: "text-grade-a" },
  down: {
    icon: TrendingDown,
    label: "empeoró vs. escaneo previo",
    className: "text-grade-f",
  },
  flat: { icon: Minus, label: "sin cambios", className: "text-on-surface-variant/60" },
};

export function TrendIndicator({
  trend,
  className,
}: {
  trend?: Trend | null;
  className?: string;
}) {
  const { icon: Icon, label, className: tone } = MAP[trend ?? "flat"];
  return (
    <span
      className={cn("inline-flex items-center", tone, className)}
      title={label}
      aria-label={label}
    >
      <Icon className="size-4" aria-hidden />
    </span>
  );
}
