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

import Link from "next/link";
import * as React from "react";

import { cn } from "@/src/application/lib/utils";
import {
  type RankingFilters,
  useRanking,
} from "@/src/application/owliver/hooks/use-ranking";
import { GRADES, gradeColorVar } from "@/src/application/owliver/lib/grade";
import type { Grade, RankingRow } from "@/src/application/owliver/schemas/api";
import { Button } from "@/src/presentation/components/ui/button";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";
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
    ? (query.data?.pages.flatMap((p) => p.data) ?? [])
    : (query.data?.pages.flatMap((p) => p.data) ?? initialRows);

  const isFiltering = filtersActive && query.isFetching && !query.data;

  return (
    <section aria-label="Ranking de seguridad de sitios">
      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="mr-1 font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
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
          <ShieldWeb className="size-3.5" /> Peor web
        </FilterChip>
        <FilterChip
          active={worst === "agentic"}
          onClick={() =>
            setWorst((cur) => (cur === "agentic" ? null : "agentic"))
          }
        >
          <AgenticChip className="size-3.5" /> Peor agéntico
        </FilterChip>
      </div>

      {/* Rows */}
      {isFiltering ? (
        <RowSkeletons />
      ) : rows.length === 0 ? (
        <EmptyRankingState
          filtersActive={filtersActive}
          onReset={() => {
            setGrade(null);
            setWorst(null);
          }}
        />
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

function EmptyRankingState({
  filtersActive,
  onReset,
}: {
  filtersActive: boolean;
  onReset: () => void;
}) {
  return (
    <div className="rounded-2xl border border-outline-variant bg-surface-container-low px-5 py-8 text-center sm:px-8">
      <div className="mx-auto max-w-lg">
        <p className="font-semibold text-foreground">
          {filtersActive
            ? "Ningún sitio coincide con ese filtro"
            : "Aún no hay sitios en el ranking"}
        </p>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">
          {filtersActive
            ? "Prueba otra combinación o vuelve al ranking completo para revisar la muestra disponible."
            : "Cuando el backend tenga resultados, aparecerán aquí ordenados de peor a mejor. Mientras tanto puedes auditar una URL específica."}
        </p>
        <div className="mt-5 flex flex-col items-center justify-center gap-2 sm:flex-row">
          {filtersActive ? (
            <Button type="button" variant="secondary" onClick={onReset}>
              Ver todos
            </Button>
          ) : null}
          <Link
            href="/scan"
            className={buttonVariants({ variant: "default", size: "default" })}
          >
            Auditar una URL
          </Link>
        </div>
      </div>
    </div>
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
        "inline-flex min-h-10 items-center gap-1.5 rounded-full border px-3.5 text-sm font-medium outline-none transition-[background-color,color,border-color,transform] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98]",
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
