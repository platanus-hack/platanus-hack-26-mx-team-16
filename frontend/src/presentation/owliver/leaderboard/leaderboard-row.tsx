/**
 * LeaderboardRow — a single Hall of Shame row (§F4). Renders WORST-FIRST as the
 * server ordered it (NEVER re-sorts): rank · big A–F grade · dependency +
 * hostname · the 🛡️/🤖 double meter · penaltyRaw tiebreak · trend · coverage
 * badges. The whole row links to `/sites/{id}`.
 *
 * Client component because it owns the "wow" micro-interactions: failing grades
 * pulse red once on mount and hovering reveals the row's top finding (the "why").
 * Both honor reduced-motion via the shared GradeBadge/animation tokens.
 */
"use client";

import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { isFailingGrade } from "@/src/application/owliver/lib/grade";
import type { RankingRow } from "@/src/application/owliver/schemas/api";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { CoverageBadges } from "@/src/presentation/owliver/components/status-badge";
import { DimensionMeter } from "@/src/presentation/owliver/leaderboard/dimension-meter";
import { TrendIndicator } from "@/src/presentation/owliver/leaderboard/trend-indicator";

export type LeaderboardRowProps = {
  row: RankingRow;
  /** Pulse failing grades once on first paint (the initial board reveal). */
  pulse?: boolean;
};

export function LeaderboardRow({ row, pulse }: LeaderboardRowProps) {
  const failing = isFailingGrade(row.overallGrade);

  return (
    <Link
      href={`/sites/${row.siteId}`}
      data-grade={row.overallGrade}
      className={cn(
        "group flex items-center gap-3 rounded-2xl border bg-card p-3 shadow-xs transition-colors hover:bg-surface-container-low md:gap-4 md:p-4",
        failing ? "border-grade-f/30" : "border-outline-variant"
      )}
    >
      <span className="w-6 shrink-0 text-center font-mono text-sm text-on-surface-variant/70 tabular-nums">
        {row.rank}
      </span>

      <GradeBadge grade={row.overallGrade} size="md" pulse={pulse} />

      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-foreground">
          {row.departmentName}
        </p>
        <p className="truncate font-mono text-xs text-on-surface-variant">
          {row.host}
        </p>
        {/* Hover reveals the "why" — the row's top finding (§F4 wow). */}
        {row.topFinding ? (
          <p className="mt-1 hidden truncate text-xs text-on-surface-variant/80 group-hover:block">
            <span className="text-grade-f">●</span> {row.topFinding}
          </p>
        ) : null}
      </div>

      <DimensionMeter
        webScore={row.webScore}
        agenticScore={row.agenticScore}
        webGrade={row.webGrade}
        agenticGrade={row.agenticGrade}
        className="hidden shrink-0 sm:flex"
      />

      <div className="hidden w-14 shrink-0 flex-col items-end md:flex">
        <span className="font-mono text-sm tabular-nums text-on-surface-variant">
          {row.penaltyRaw}
        </span>
        <span className="text-[10px] uppercase tracking-wide text-on-surface-variant/50">
          penaliz.
        </span>
      </div>

      <TrendIndicator trend={row.trend} className="hidden shrink-0 md:inline-flex" />

      <CoverageBadges
        agenticStatus={row.agenticStatus}
        partialCoverage={row.partialCoverage}
        className="hidden shrink-0 lg:inline-flex max-w-44"
      />
    </Link>
  );
}
