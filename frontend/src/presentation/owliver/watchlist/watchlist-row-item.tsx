/**
 * WatchlistRowItem (§F11) — one watched domain: grade + 🛡️/🤖 sub-grades + last
 * scan + the `monitor` Switch + re-scan + remove. The mutation key is the
 * watchlist-ROW `id` (NEVER siteId — see schemas/api.ts). Optimistic-ish: the
 * Switch is disabled while its PATCH is in flight.
 */
"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Loader2, Play, Trash2 } from "lucide-react";

import { gradeColorVar } from "@/src/application/owliver/lib/grade";
import type { WatchlistRow } from "@/src/application/owliver/schemas/api";
import {
  useRemoveWatchlist,
  useToggleMonitor,
} from "@/src/application/owliver/hooks/use-watchlist";
import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { CoverageBadges } from "@/src/presentation/owliver/components/status-badge";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

function lastScanLabel(iso: string | null | undefined): string {
  if (!iso) return "Nunca escaneado";
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function MiniGrade({
  label,
  grade,
}: {
  label: ReactNode;
  grade: WatchlistRow["webGrade"];
}) {
  return (
    <span className="inline-flex items-center gap-1 font-mono text-xs">
      <span className="flex text-on-surface-variant">{label}</span>
      {grade ? (
        <span
          className="font-semibold"
          style={{ color: gradeColorVar(grade) }}
        >
          {grade}
        </span>
      ) : (
        <span className="text-on-surface-variant">—</span>
      )}
    </span>
  );
}

export function WatchlistRowItem({ row }: { row: WatchlistRow }) {
  const toggle = useToggleMonitor();
  const remove = useRemoveWatchlist();

  return (
    <li className="flex flex-wrap items-center gap-4 rounded-2xl border border-outline-variant bg-card p-4 shadow-xs">
      {row.overallGrade ? (
        <Link href={`/sites/${row.siteId}`} aria-label={`Ver ${row.host}`}>
          <GradeBadge grade={row.overallGrade} size="md" />
        </Link>
      ) : (
        <span className="inline-flex h-10 min-w-10 items-center justify-center rounded-xl border border-dashed border-outline-variant font-mono text-sm text-on-surface-variant">
          —
        </span>
      )}

      <div className="min-w-0 flex-1">
        <Link
          href={`/sites/${row.siteId}`}
          className="truncate font-medium text-foreground hover:underline"
        >
          {row.departmentName ?? row.host}
        </Link>
        <p className="truncate font-mono text-xs text-on-surface-variant">
          {row.host}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-3">
          <MiniGrade
            label={<ShieldWeb className="size-3.5 text-primary" />}
            grade={row.webGrade}
          />
          <MiniGrade
            label={<AgenticChip className="size-3.5 text-tertiary" />}
            grade={row.agenticGrade}
          />
          <span className="font-mono text-xs text-on-surface-variant">
            {lastScanLabel(row.lastScanAt)}
          </span>
          <CoverageBadges agenticStatus={row.agenticStatus} />
        </div>
      </div>

      {/* Monitor toggle */}
      <label className="flex shrink-0 items-center gap-2">
        <span className="text-sm text-on-surface-variant">Monitoreo</span>
        <Switch
          checked={row.monitor}
          disabled={toggle.isPending}
          onCheckedChange={(checked) =>
            toggle.mutate({ id: row.id, monitor: checked })
          }
          aria-label={`Monitoreo de ${row.host}`}
        />
      </label>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          nativeButton={false}
          render={<Link href={`/scan?url=${encodeURIComponent(row.host)}`} />}
        >
          <Play className="size-3.5" aria-hidden />
          Re-escanear
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Quitar ${row.host} de la watchlist`}
          disabled={remove.isPending}
          onClick={() => remove.mutate(row.id)}
        >
          {remove.isPending ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Trash2 className="size-4 text-on-surface-variant" aria-hidden />
          )}
        </Button>
      </div>
    </li>
  );
}
