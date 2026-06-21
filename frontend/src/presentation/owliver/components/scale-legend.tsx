/**
 * ScaleLegend — the A–F grade scale key (DESIGN.md §2 "Grade-Is-Data"). Renders
 * the full ramp with its color swatch, letter (mono), band label, and the score
 * threshold, so any screen can show "what the grades mean". Color comes only from
 * `gradeColorVar` — never a hardcoded hex.
 */
import { cn } from "@/src/application/lib/utils";
import { GRADES, gradeColorVar, gradeLabel } from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";

/** Display-only threshold copy per grade (07-scoring bands). */
const BAND: Record<Grade, string> = {
  A: "≥ 90",
  B: "≥ 80",
  C: "≥ 70",
  D: "≥ 60",
  E: "≥ 40",
  F: "< 40",
};

export type ScaleLegendProps = {
  className?: string;
  /** Horizontal compact row (default) vs. a vertical stacked list. */
  orientation?: "horizontal" | "vertical";
};

export function ScaleLegend({
  className,
  orientation = "horizontal",
}: ScaleLegendProps) {
  return (
    <ul
      data-slot="scale-legend"
      className={cn(
        "flex gap-2 text-xs",
        orientation === "horizontal" ? "flex-wrap items-center" : "flex-col",
        className
      )}
    >
      {GRADES.map((g) => (
        <li key={g} className="inline-flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-flex size-5 items-center justify-center rounded-md font-mono text-[11px] font-bold text-[color:#171105]"
            style={{ backgroundColor: gradeColorVar(g) }}
          >
            {g}
          </span>
          <span className="text-on-surface-variant">
            {gradeLabel(g)}{" "}
            <span className="font-mono tabular-nums opacity-70">{BAND[g]}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
