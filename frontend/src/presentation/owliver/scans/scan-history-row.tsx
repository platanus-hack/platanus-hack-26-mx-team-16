/**
 * ScanHistoryRow — one run in `/scans`. The whole row is a link to where the run
 * actually lives: a finished run (`done`/`partial`) opens its full report; an
 * in-flight or failed run opens the live theater. It reuses the product's grade,
 * dimension-meter, trend and coverage primitives so a row reads exactly like a
 * leaderboard row — the same vocabulary, screen to screen.
 *
 * No grade yet → a status glyph + pill carry the state in TEXT (never color
 * alone). Running rows animate their wavy progress; failed rows surface the
 * error; hovering reveals the "why" (top finding).
 */
import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import type { ScanHistoryItem } from "@/src/application/owliver/fixtures";
import type { ScanLevel } from "@/src/application/owliver/schemas/api";
import { InlineMeta } from "@/src/presentation/components/common/inline-meta";
import { WavyProgress } from "@/src/presentation/components/common/wavy-progress";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { CoverageBadges } from "@/src/presentation/owliver/components/status-badge";
import { DimensionMeter } from "@/src/presentation/owliver/leaderboard/dimension-meter";
import { TrendIndicator } from "@/src/presentation/owliver/leaderboard/trend-indicator";
import {
  ScanStatusGlyph,
  ScanStatusPill,
  SCAN_STATUS_META,
} from "@/src/presentation/owliver/scans/scan-status";

const LEVEL_LABEL: Record<ScanLevel, string> = {
  basico: "Nivel básico",
  intermedio: "Nivel intermedio",
  avanzado: "Nivel avanzado",
};

/** Finished runs → the full report; everything else → the live theater. */
export function scanHref(item: ScanHistoryItem): string {
  return item.status === "done" || item.status === "partial"
    ? `/scans/${item.scanId}/report`
    : `/scans/${item.scanId}`;
}

function referenceTimestamp(item: ScanHistoryItem): string | null {
  return item.finishedAt ?? item.startedAt ?? item.createdAt ?? null;
}

function findingsSummary(item: ScanHistoryItem): string {
  const f = `${item.findingsCount} ${item.findingsCount === 1 ? "hallazgo" : "hallazgos"}`;
  if (item.criticalCount > 0) {
    return `${f} · ${item.criticalCount} ${item.criticalCount === 1 ? "crítico" : "críticos"}`;
  }
  return f;
}

export function ScanHistoryRow({ item }: { item: ScanHistoryItem }) {
  const graded = item.overallGrade != null;
  const isGradedView = item.status === "done" || item.status === "partial";
  const isRunning = item.status === "running";
  const isFailed = item.status === "failed";
  const rel = formatRelativeDate(referenceTimestamp(item));

  const ariaLabel = `${item.departmentName ?? item.host} — ${item.host}, ${
    graded ? `grado ${item.overallGrade}` : SCAN_STATUS_META[item.status].label
  }, ${rel}`;

  return (
    <Link
      href={scanHref(item)}
      data-grade={item.overallGrade ?? undefined}
      aria-label={ariaLabel}
      className={cn(
        "group flex items-center gap-3 rounded-2xl border bg-card p-3 shadow-xs outline-none transition-[background-color,box-shadow,transform] hover:bg-surface-container-low focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.998] md:gap-4 md:p-4",
        isFailed ? "border-destructive/30" : "border-outline-variant"
      )}
    >
      {/* Outcome: the grade, or a status glyph standing in until there is one. */}
      {item.overallGrade ? (
        <GradeBadge grade={item.overallGrade} size="md" className="shrink-0" />
      ) : (
        <ScanStatusGlyph
          status={item.status}
          progress={item.progress}
          className="shrink-0"
        />
      )}

      {/* Identity + state */}
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-foreground">
          {item.departmentName ?? item.host}
        </p>

        <p className="flex min-w-0 flex-wrap items-center gap-x-0.5 gap-y-1 text-xs text-on-surface-variant">
          <span className="truncate font-mono">{item.host}</span>
          <InlineMeta variant="text">{LEVEL_LABEL[item.level]}</InlineMeta>
          <InlineMeta variant="text">{rel}</InlineMeta>
        </p>

        {/* Third line — the live, failed or settled state of the run. */}
        {isRunning ? (
          <div className="mt-2 flex items-center gap-2">
            <WavyProgress value={item.progress} height={8} className="max-w-44" />
            <span className="truncate text-xs text-on-surface-variant">
              {item.currentPhase ?? "Preparando…"}
            </span>
          </div>
        ) : isFailed ? (
          <p className="mt-1 truncate text-xs text-destructive">
            {item.error ?? "El escaneo no pudo completarse."}
          </p>
        ) : item.status === "queued" ? (
          <p className="mt-1">
            <ScanStatusPill status="queued" />
          </p>
        ) : (
          <p className="mt-1 flex items-center gap-2 text-xs text-on-surface-variant">
            <span>{findingsSummary(item)}</span>
            {/* The "why", revealed on hover/focus like the leaderboard rows. */}
            {item.topFinding ? (
              <span className="hidden min-w-0 items-center gap-1 truncate text-on-surface-variant group-hover:flex group-focus-visible:flex">
                <span aria-hidden className="text-grade-f">
                  ●
                </span>
                <span className="truncate">{item.topFinding}</span>
              </span>
            ) : null}
          </p>
        )}
      </div>

      {/* Right cluster — only meaningful once a run has scores. */}
      {isGradedView ? (
        <DimensionMeter
          webScore={item.webScore}
          agenticScore={item.agenticScore}
          webGrade={item.webGrade}
          agenticGrade={item.agenticGrade}
          className="hidden shrink-0 sm:flex"
        />
      ) : null}

      {graded && item.trend ? (
        <TrendIndicator
          trend={item.trend}
          className="hidden shrink-0 md:inline-flex"
        />
      ) : null}

      {item.agenticStatus ? (
        <CoverageBadges
          agenticStatus={item.agenticStatus}
          partialCoverage={item.partialCoverage}
          className="hidden max-w-44 shrink-0 lg:inline-flex"
        />
      ) : null}

      <ChevronRight
        className="size-4 shrink-0 text-on-surface-variant/50 transition-transform group-hover:translate-x-0.5"
        aria-hidden
      />
    </Link>
  );
}
