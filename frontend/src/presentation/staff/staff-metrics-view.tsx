"use client";

import { BarChart3, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import {
  backendErrorMessage,
  useStaffMetricsQuery,
} from "@/src/application/hooks/queries/staff-tasks";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Button } from "@/src/presentation/components/ui/button";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";
import { shortActor } from "./staff-queue-view";

/** Tipos contados por el backend (case_events). */
const COUNTED_TYPES = [
  "qa.passed",
  "qa.failed",
  "qa.sampled",
  "review.approved",
  "review.skipped",
] as const;

const TYPE_LABELS: Record<string, string> = {
  "qa.passed": "QA aprobadas",
  "qa.failed": "QA fallidas",
  "qa.sampled": "QA muestreadas",
  "review.approved": "Revisiones aprobadas",
  "review.skipped": "Auto-aprobadas",
};

function num(map: Record<string, number>, key: string): number {
  return map[key] ?? 0;
}

function passRate(map: Record<string, number>): string {
  const passed = num(map, "qa.passed");
  const failed = num(map, "qa.failed");
  const audited = passed + failed;
  if (audited === 0) return "—";
  return `${Math.round((passed / audited) * 100)}%`;
}

/**
 * E6 · W8 — métricas QA del plano staff (`GET /staff/v1/metrics`, staff_admin).
 * Tarjetas de conteo simples + tablas por tenant y por analista. No es el
 * dashboard grande del plan; es la lectura barata sobre los case_events.
 */
export function StaffMetricsView() {
  const metricsQuery = useStaffMetricsQuery();
  const metrics = metricsQuery.data;

  const tenantRows = useMemo(
    () => Object.entries(metrics?.byTenant ?? {}),
    [metrics?.byTenant]
  );
  const actorRows = useMemo(
    () => Object.entries(metrics?.byActor ?? {}),
    [metrics?.byActor]
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Métricas QA</h1>
          <p className="text-sm text-muted-foreground">
            {metrics?.since
              ? `Conteos desde ${new Date(metrics.since).toLocaleDateString()}.`
              : "Conteos de auditoría QA y aprobaciones por tenant y analista."}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => metricsQuery.refetch()}
          aria-label="Refrescar"
        >
          <RefreshCw className="size-4" />
        </Button>
      </div>

      {metricsQuery.isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={`metric-skeleton-${i + 1}`} className="h-20 w-full" />
          ))}
        </div>
      ) : metricsQuery.isError ? (
        <p className="text-sm text-destructive">
          {backendErrorMessage(metricsQuery.error)}
        </p>
      ) : !metrics ? (
        <EmptyState
          icon={BarChart3}
          title="Sin métricas"
          description="Aún no hay eventos para el periodo seleccionado."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
            {COUNTED_TYPES.map((type) => (
              <div
                key={type}
                className="rounded-xl border bg-card p-4 shadow-xs"
              >
                <p className="text-xs text-muted-foreground">
                  {TYPE_LABELS[type]}
                </p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {num(metrics.totals, type)}
                </p>
              </div>
            ))}
            <div className="rounded-xl border bg-card p-4 shadow-xs">
              <p className="text-xs text-muted-foreground">QA pass rate</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {passRate(metrics.totals)}
              </p>
            </div>
          </div>

          <MetricsTable
            title="Por tenant"
            label="Tenant"
            rows={tenantRows}
            renderKey={(id) => id}
          />
          <MetricsTable
            title="Por analista"
            label="Analista"
            rows={actorRows}
            renderKey={(actor) => shortActor(actor)}
          />
        </>
      )}
    </div>
  );
}

function MetricsTable({
  title,
  label,
  rows,
  renderKey,
}: {
  title: string;
  label: string;
  rows: Array<[string, Record<string, number>]>;
  renderKey: (key: string) => string;
}) {
  if (rows.length === 0) return null;
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-medium text-muted-foreground">{title}</h2>
      <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{label}</TableHead>
              <TableHead className="text-right">QA pass</TableHead>
              <TableHead className="text-right">QA fail</TableHead>
              <TableHead className="text-right">Auto-aprob.</TableHead>
              <TableHead className="text-right">Aprobadas</TableHead>
              <TableHead className="text-right">Pass rate</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(([key, counts]) => (
              <TableRow key={key}>
                <TableCell className="font-mono text-xs" title={key}>
                  {renderKey(key)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {num(counts, "qa.passed")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {num(counts, "qa.failed")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {num(counts, "review.skipped")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {num(counts, "review.approved")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {passRate(counts)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
