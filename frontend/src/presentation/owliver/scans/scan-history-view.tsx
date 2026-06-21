/**
 * ScanHistoryView — the `/scans` history (§F6). The signed-in user's run log as a
 * scannable, time-grouped list: a quiet readout strip up top, a search + status +
 * sort toolbar, then the runs grouped Hoy / Esta semana / Anteriores so the shape
 * is legible at a glance. Worst-first sort drops the time groups for a single
 * severity-ordered list.
 *
 * Client island: it owns the search/filter/sort state and the entrance stagger.
 * Every row links out to the report (finished) or the live theater (in-flight),
 * so the list is purely a router into the work — no data is computed here.
 */
"use client";

import { Radar, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { cn } from "@/src/application/lib/utils";
import type { ScanHistoryItem } from "@/src/application/owliver/fixtures";
import { gradeLabel } from "@/src/application/owliver/lib/grade";
import type { Grade } from "@/src/application/owliver/schemas/api";
import { CountUp } from "@/src/presentation/components/common/count-up";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { Input } from "@/src/presentation/components/ui/input";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";
import { ScanHistoryRow } from "@/src/presentation/owliver/scans/scan-history-row";

const GRADE_RANK: Grade[] = ["A", "B", "C", "D", "E", "F"];

type StatusFilter = "all" | "active" | "done" | "failed";
type SortKey = "recent" | "grade";

const DAY_MS = 86_400_000;

function referenceMs(item: ScanHistoryItem): number {
  const ts = item.finishedAt ?? item.startedAt ?? item.createdAt;
  const ms = ts ? new Date(ts).getTime() : NaN;
  return Number.isNaN(ms) ? 0 : ms;
}

function matchesStatus(item: ScanHistoryItem, filter: StatusFilter): boolean {
  switch (filter) {
    case "active":
      return item.status === "running" || item.status === "queued";
    case "done":
      return item.status === "done" || item.status === "partial";
    case "failed":
      return item.status === "failed" || item.status === "cancelled";
    default:
      return true;
  }
}

/** Worst grade present (F → A); used in the readout strip. */
function worstGrade(items: ScanHistoryItem[]): Grade | null {
  let worst: Grade | null = null;
  for (const it of items) {
    if (!it.overallGrade) continue;
    if (
      !worst ||
      GRADE_RANK.indexOf(it.overallGrade) > GRADE_RANK.indexOf(worst)
    ) {
      worst = it.overallGrade;
    }
  }
  return worst;
}

type Bucket = { key: string; label: string; items: ScanHistoryItem[] };

function groupByTime(items: ScanHistoryItem[]): Bucket[] {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const todayMs = startOfToday.getTime();
  const weekMs = todayMs - 6 * DAY_MS;

  const buckets: Record<string, ScanHistoryItem[]> = {
    today: [],
    week: [],
    older: [],
  };
  for (const it of items) {
    const ms = referenceMs(it);
    if (ms >= todayMs) buckets.today.push(it);
    else if (ms >= weekMs) buckets.week.push(it);
    else buckets.older.push(it);
  }
  return [
    { key: "today", label: "Hoy", items: buckets.today },
    { key: "week", label: "Esta semana", items: buckets.week },
    { key: "older", label: "Anteriores", items: buckets.older },
  ].filter((b) => b.items.length > 0);
}

function ReadoutStat({
  value,
  label,
  badge,
  tone,
}: {
  value?: number;
  label: string;
  badge?: React.ReactNode;
  tone?: "default" | "alert";
}) {
  return (
    <div className="flex flex-col gap-1 px-4 first:pl-0 sm:px-6">
      <span
        className={cn(
          "font-mono text-2xl font-semibold leading-none tabular-nums",
          tone === "alert" ? "text-destructive" : "text-foreground"
        )}
      >
        {badge ?? (typeof value === "number" ? <CountUp to={value} /> : "—")}
      </span>
      <span className="text-xs text-on-surface-variant">{label}</span>
    </div>
  );
}

export function ScanHistoryView({ items }: { items: ScanHistoryItem[] }) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [sort, setSort] = useState<SortKey>("recent");

  // Totals are run-level (not affected by the active filter).
  const totals = useMemo(() => {
    const active = items.filter(
      (i) => i.status === "running" || i.status === "queued"
    ).length;
    const criticals = items.reduce((n, i) => n + i.criticalCount, 0);
    return { total: items.length, active, criticals, worst: worstGrade(items) };
  }, [items]);

  const statusCounts = useMemo(
    () => ({
      all: items.length,
      active: items.filter((i) => matchesStatus(i, "active")).length,
      done: items.filter((i) => matchesStatus(i, "done")).length,
      failed: items.filter((i) => matchesStatus(i, "failed")).length,
    }),
    [items]
  );

  const filtered = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    const next = items.filter((i) => {
      if (!matchesStatus(i, status)) return false;
      if (!q) return true;
      return (
        i.host.toLowerCase().includes(q) ||
        (i.departmentName ?? "").toLowerCase().includes(q)
      );
    });
    if (sort === "grade") {
      return [...next].sort((a, b) => {
        const ra = a.overallGrade ? GRADE_RANK.indexOf(a.overallGrade) : -1;
        const rb = b.overallGrade ? GRADE_RANK.indexOf(b.overallGrade) : -1;
        if (rb !== ra) return rb - ra; // worst (F) first
        return referenceMs(b) - referenceMs(a);
      });
    }
    return [...next].sort((a, b) => referenceMs(b) - referenceMs(a));
  }, [items, deferredQuery, status, sort]);

  const groups: Bucket[] =
    sort === "grade"
      ? [{ key: "grade", label: "Por gravedad", items: filtered }]
      : groupByTime(filtered);

  const STATUS_TABS: { value: StatusFilter; label: string; count: number }[] = [
    { value: "all", label: "Todos", count: statusCounts.all },
    { value: "active", label: "En curso", count: statusCounts.active },
    { value: "done", label: "Completos", count: statusCounts.done },
    { value: "failed", label: "Fallidos", count: statusCounts.failed },
  ];

  // A running stagger index across buckets keeps the entrance coherent.
  let revealIndex = 0;

  const hasScans = items.length > 0;
  const hasResults = filtered.length > 0;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:px-6 md:py-14">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-primary-container px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wide text-on-primary-container">
            <span className="size-2 rounded-full bg-primary" aria-hidden />
            Banco de inspección
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-balance text-foreground md:text-4xl">
            Mis escaneos
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant md:text-base">
            El historial de cada auditoría que has ejecutado. Abre un escaneo
            terminado para ver su reporte completo, o sigue uno en vivo.
          </p>
        </div>
        <Link
          href="/scan"
          className={buttonVariants({ variant: "default", size: "lg" })}
        >
          <Radar className="size-4" />
          Auditar Página
        </Link>
      </header>

      {hasScans ? (
        <>
          {/* Readout strip — quiet, not a metric wall */}
          <div className="mt-8 flex flex-wrap items-center gap-y-4 divide-x divide-outline-variant rounded-2xl border border-outline-variant bg-surface-container-low px-5 py-4">
            <ReadoutStat value={totals.total} label="Escaneos" />
            <ReadoutStat value={totals.active} label="En curso" />
            <ReadoutStat
              value={totals.criticals}
              label="Hallazgos críticos"
              tone={totals.criticals > 0 ? "alert" : "default"}
            />
            <ReadoutStat
              label="Peor grado"
              badge={
                totals.worst ? (
                  <span className="inline-flex items-center gap-2">
                    <GradeBadge grade={totals.worst} size="sm" />
                    <span className="text-sm font-normal text-on-surface-variant">
                      {gradeLabel(totals.worst)}
                    </span>
                  </span>
                ) : undefined
              }
            />
          </div>

          {/* Toolbar */}
          <div className="mt-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-xs">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-on-surface-variant"
                aria-hidden
              />
              <Input
                type="search"
                value={query}
                onValueChange={setQuery}
                placeholder="Buscar por dominio u organización…"
                aria-label="Buscar escaneos"
                className="pl-9"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Status segmented control */}
              <div
                role="tablist"
                aria-label="Filtrar por estado"
                className="inline-flex items-center gap-1 rounded-full border border-outline-variant bg-surface-container-low p-1 shadow-xs"
              >
                {STATUS_TABS.map((tab) => {
                  const active = status === tab.value;
                  return (
                    <button
                      key={tab.value}
                      type="button"
                      role="tab"
                      aria-selected={active}
                      onClick={() => setStatus(tab.value)}
                      className={cn(
                        "inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium outline-none transition-[background-color,color,box-shadow,transform] focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]",
                        active
                          ? "bg-primary-action text-primary-action-foreground shadow-[0_2px_8px_rgba(104,88,242,0.24)]"
                          : "text-on-surface-variant hover:bg-primary-container/55 hover:text-foreground"
                      )}
                    >
                      {tab.label}
                      <span
                        className={cn(
                          "rounded-full px-1.5 font-mono text-[11px] tabular-nums",
                          active
                            ? "bg-white/20 text-white"
                            : "text-on-surface-variant/60"
                        )}
                      >
                        {tab.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Sort */}
              <div className="inline-flex items-center gap-1 rounded-full border border-outline-variant bg-surface-container-low p-1 shadow-xs">
                <SlidersHorizontal
                  className="ml-2 size-3.5 text-on-surface-variant"
                  aria-hidden
                />
                {(
                  [
                    { value: "recent", label: "Recientes" },
                    { value: "grade", label: "Peor grado" },
                  ] as { value: SortKey; label: string }[]
                ).map((opt) => {
                  const active = sort === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setSort(opt.value)}
                      className={cn(
                        "min-h-9 cursor-pointer rounded-full px-3.5 py-1.5 text-sm font-medium outline-none transition-[background-color,color,box-shadow,transform] focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]",
                        active
                          ? "bg-primary-action text-primary-action-foreground shadow-[0_2px_8px_rgba(104,88,242,0.24)]"
                          : "text-on-surface-variant hover:bg-primary-container/55 hover:text-foreground"
                      )}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* List */}
          {hasResults ? (
            <div className="mt-6 space-y-8">
              {groups.map((group) => (
                <section key={group.key} aria-label={group.label}>
                  <h2 className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
                    {group.label}
                    <span className="text-on-surface-variant/50">
                      {group.items.length}
                    </span>
                  </h2>
                  <div className="space-y-2.5">
                    {group.items.map((item) => {
                      const delay = Math.min(revealIndex++, 12) * 35;
                      return (
                        <Reveal key={item.scanId} delay={delay}>
                          <ScanHistoryRow item={item} />
                        </Reveal>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            // Filters matched nothing (but the user does have scans).
            <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant px-6 py-14 text-center">
              <p className="text-base font-medium text-foreground">
                Sin escaneos para estos filtros
              </p>
              <p className="mt-1 max-w-sm text-sm text-on-surface-variant">
                Ajusta la búsqueda o el estado para ver más resultados.
              </p>
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setStatus("all");
                }}
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "mt-5"
                )}
              >
                Limpiar filtros
              </button>
            </div>
          )}
        </>
      ) : (
        // First run — no scans yet.
        <div className="mt-10 flex flex-col items-center justify-center rounded-3xl border border-outline-variant bg-surface-container-low px-6 py-16 text-center">
          <OwlMascot state="idle" size={72} />
          <h2 className="mt-5 text-xl font-semibold text-foreground">
            Aún no has auditado ningún sitio
          </h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-on-surface-variant">
            Cuando ejecutes tu primer escaneo, aparecerá aquí con su grado A–F,
            sus hallazgos y el reporte completo de la ejecución.
          </p>
          <Link
            href="/scan"
            className={cn(
              buttonVariants({ variant: "default", size: "lg" }),
              "mt-6"
            )}
          >
            <Radar className="size-4" />
            Auditar mi primera URL
          </Link>
        </div>
      )}
    </div>
  );
}
