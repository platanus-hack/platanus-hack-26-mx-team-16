/**
 * HeroStats — the provocative subcopy counter on the Hall of Shame hero (§F4):
 * "{total} sitios auditados · {failing} reprobados (grado F)". The two numbers
 * count up on mount (the grade-reveal motion language), with the failing count
 * in grade-F red. Reduced-motion users get the final values instantly (CountUp
 * already honors `prefers-reduced-motion`).
 */
"use client";

import { CountUp } from "@/src/presentation/components/common/count-up";

export type HeroStatsProps = {
  total: number;
  failing: number;
};

export function HeroStats({ total, failing }: HeroStatsProps) {
  return (
    <p className="mt-3 text-lg text-on-surface-variant">
      <CountUp to={total} className="font-mono font-semibold tabular-nums text-foreground" />{" "}
      sitios auditados ·{" "}
      <span className="font-semibold text-grade-f">
        <CountUp to={failing} className="font-mono tabular-nums" /> reprobados
        (grado F)
      </span>
    </p>
  );
}
