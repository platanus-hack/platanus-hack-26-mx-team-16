/**
 * LeaderboardBoard — the interactive Hall of Shame table (§F4). The page renders
 * the first page as RSC (worst-first, server-authoritative) and hands it here as
 * `initialRows` so there's never a blank flash; this client component then owns
 * the filters (by grade · by worst dimension), the "cargar más" cursor pagination
 * (via `useRanking`), and the per-row micro-interactions.
 *
 * INVARIANT: we NEVER re-sort. The server's `(overall_grade DESC, penalty_raw
 * DESC)` worst-first order is authoritative; filters are forwarded as query
 * params and the merged pages keep server order.
 */
"use client";

import * as React from "react";

import { cn } from "@/src/application/lib/utils";
import {
  type RankingFilters,
  useRanking,
} from "@/src/application/owliver/hooks/use-ranking";
import { GRADES, gradeColorVar } from "@/src/application/owliver/lib/grade";
import type { Grade, RankingRow } from "@/src/application/owliver/schemas/api";
import { Button } from "@/src/presentation/components/ui/button";
import { LeaderboardRow } from "@/src/presentation/owliver/leaderboard/leaderboard-row";

export type LeaderboardBoardProps = {
  /** First page rendered server-side (worst-first). Shown until a filter/page. */
  initialRows: RankingRow[];
  country?: string;
};

type WorstFilter = "web" | "agentic" | null;

export function LeaderboardBoard({
  initialRows,
  country = "mx",
}: LeaderboardBoardProps) {
  const [grade, setGrade] = React.useState<Grade | null>(null);
  const [worst, setWorst] = React.useState<WorstFilter>(null);

  const filtersActive = grade !== null || worst !== null;
  const filters: RankingFilters = {
    country,
    ...(grade ? { grade } : {}),
    ...(worst ? { worst } : {}),
  };

  const query = useRanking(filters);

  // Until the user touches a filter we show the RSC-provided rows verbatim so
  // there is zero loading flash on first paint. Once interactive, the query
  // (which the BFF also serves from the same fixture) drives the board.
  const rows: RankingRow[] = filtersActive
    ? query.data?.pages.flatMap((p) => p.data) ?? []
    : query.data?.pages.flatMap((p) => p.data) ?? initialRows;

  const isFiltering = filtersActive && query.isFetching && !query.data;

  return (
    <section aria-label="Ranking de sitios del Estado">
      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-xs font-medium uppercase tracking-wide text-on-surface-variant/70">
          Filtrar
        </span>
        <FilterChip
          active={grade === null && worst === null}
          onClick={() => {
            setGrade(null);
            setWorst(null);
          }}
        >
          Todos
        </FilterChip>
        {GRADES.map((g) => (
          <FilterChip
            key={g}
            active={grade === g}
            onClick={() => setGrade((cur) => (cur === g ? null : g))}
            dotColor={gradeColorVar(g)}
          >
            {g}
          </FilterChip>
        ))}
        <span className="mx-1 h-4 w-px bg-outline-variant" aria-hidden />
        <FilterChip
          active={worst === "web"}
          onClick={() => setWorst((cur) => (cur === "web" ? null : "web"))}
        >
          🛡️ Peor web
        </FilterChip>
        <FilterChip
          active={worst === "agentic"}
          onClick={() =>
            setWorst((cur) => (cur === "agentic" ? null : "agentic"))
          }
        >
          🤖 Peor agéntico
        </FilterChip>
      </div>

      {/* Rows */}
      {isFiltering ? (
        <RowSkeletons />
      ) : rows.length === 0 ? (
        <p className="rounded-2xl border border-outline-variant bg-card p-8 text-center text-sm text-on-surface-variant">
          Ningún sitio coincide con el filtro.
        </p>
      ) : (
        <ol className="space-y-2">
          {rows.map((row, i) => (
            <li key={row.siteId}>
              <LeaderboardRow row={row} pulse={!filtersActive && i < 12} />
            </li>
          ))}
        </ol>
      )}

      {/* Cargar más */}
      {query.hasNextPage ? (
        <div className="mt-6 flex justify-center">
          <Button
            variant="outline"
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? "Cargando…" : "Cargar más"}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

function FilterChip({
  active,
  onClick,
  children,
  dotColor,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  dotColor?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-sm font-medium transition-colors",
        active
          ? "border-transparent bg-primary text-primary-foreground"
          : "border-outline-variant bg-card text-on-surface-variant hover:bg-surface-container-low"
      )}
    >
      {dotColor ? (
        <span
          aria-hidden
          className="size-2 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
      ) : null}
      {children}
    </button>
  );
}

function RowSkeletons() {
  return (
    <ol className="space-y-2" aria-hidden>
      {Array.from({ length: 8 }).map((_, i) => (
        <li
          // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton placeholders
          key={i}
          className="flex h-[68px] animate-pulse items-center gap-4 rounded-2xl border border-outline-variant bg-surface-container-low p-4"
        >
          <span className="size-10 rounded-xl bg-surface-container-high" />
          <span className="h-4 w-48 rounded bg-surface-container-high" />
        </li>
      ))}
    </ol>
  );
}
