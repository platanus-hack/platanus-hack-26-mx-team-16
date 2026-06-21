/**
 * GradeBadge — the A–F grade as a squircle chip in Roboto Mono (DESIGN.md §7).
 * Color comes ONLY from the `--grade-*` ramp via `gradeColorVar` (the single
 * source of state color). Accessible: the letter + an sr-only label, never
 * color alone (§F12).
 *
 * Works in both the light app-shell and the SOC theater (the grade ramp is not
 * themed away).
 */
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/src/application/lib/utils";
import {
  gradeColorVar,
  gradeLabel,
  isFailingGrade,
} from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";

const gradeBadgeVariants = cva(
  "inline-flex items-center justify-center font-mono font-semibold leading-none select-none tabular-nums",
  {
    variants: {
      size: {
        sm: "h-7 min-w-7 rounded-lg px-1.5 text-sm",
        md: "h-10 min-w-10 rounded-xl px-2 text-xl",
        lg: "h-16 min-w-16 rounded-2xl px-3 text-4xl",
        xl: "h-24 min-w-24 rounded-3xl px-4 text-6xl",
      },
      tone: {
        /** Solid pastel fill with dark ink — the default hero look. */
        solid: "text-[color:#171105]",
        /** Tinted (10% fill) — quieter, for dense rows. */
        soft: "",
      },
    },
    defaultVariants: { size: "md", tone: "solid" },
  }
);

export type GradeBadgeProps = VariantProps<typeof gradeBadgeVariants> & {
  grade: Grade;
  className?: string;
  /** Pulse once in red on mount (failing grades only). Handled by the caller's
   *  animation class — set via `pulse` to add `animate-pulse-once`. */
  pulse?: boolean;
};

export function GradeBadge({
  grade,
  size,
  tone,
  pulse,
  className,
}: GradeBadgeProps) {
  const color = gradeColorVar(grade);
  const style =
    tone === "soft"
      ? {
          backgroundColor: `color-mix(in oklab, ${color} 16%, transparent)`,
          color,
        }
      : { backgroundColor: color };

  return (
    <span
      data-slot="grade-badge"
      data-grade={grade}
      role="img"
      aria-label={`Grado ${grade} — ${gradeLabel(grade)}`}
      className={cn(
        gradeBadgeVariants({ size, tone }),
        pulse && isFailingGrade(grade) && "animate-pulse-once",
        className
      )}
      style={style}
    >
      <span aria-hidden>{grade}</span>
    </span>
  );
}
