/**
 * `/watchlist` — Watchlist + monitoring management (§F11, PROTECTED). The
 * signed-in user adds domains, toggles `monitor` per row (re-scans), removes
 * rows, and edits account alert prefs. All data flows through the BFF
 * (`/api/owliver/watchlist`, `/api/owliver/me/alerts`), which falls back to
 * fixtures for GET so the screen renders without a backend.
 *
 * Client component (state: add form, switches, alert prefs). Auth is gated by
 * the parent `(protected)` layout (cookie refresh → /login). Each row's mutation
 * key is the watchlist-ROW `id`, never siteId.
 */
"use client";

import { Eye } from "lucide-react";

import { useWatchlist } from "@/src/application/owliver/hooks/use-watchlist";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { AddDomainForm } from "@/src/presentation/owliver/watchlist/add-domain-form";
import { AlertPrefsPanel } from "@/src/presentation/owliver/watchlist/alert-prefs-panel";
import { WatchlistRowItem } from "@/src/presentation/owliver/watchlist/watchlist-row-item";

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-outline-variant bg-card p-4">
      <Skeleton className="size-10 rounded-xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-32" />
      </div>
      <Skeleton className="h-7 w-12 rounded-full" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-outline-variant bg-card px-6 py-14 text-center">
      <OwlMascot state="idle" size={64} />
      <h2 className="mt-5 text-lg font-semibold text-foreground">
        Tu watchlist está vacía
      </h2>
      <p className="mt-2 max-w-sm text-sm text-on-surface-variant">
        Agrega tu primer dominio para vigilarlo. Owliver lo re-escanea
        periódicamente y te avisa cuando su grado empeora.
      </p>
    </div>
  );
}

export default function WatchlistPage() {
  const { data, isLoading, isError } = useWatchlist();
  const rows = data ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:px-6">
      <header className="mb-8">
        <div className="flex items-center gap-2">
          <Eye className="size-5 text-primary" aria-hidden />
          <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
            Watchlist
          </h1>
        </div>
        <p className="mt-2 text-on-surface-variant">
          Vigila tus dominios y activa el monitoreo continuo. Los resultados de
          escaneos activos son privados de tu cuenta.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main column: add form + rows */}
        <div className="space-y-6">
          <AddDomainForm />

          {isLoading ? (
            <div className="space-y-2">
              <RowSkeleton />
              <RowSkeleton />
              <RowSkeleton />
            </div>
          ) : isError ? (
            <div
              className="rounded-2xl border border-outline-variant bg-card px-6 py-10 text-center text-sm text-on-surface-variant"
              role="alert"
            >
              No pudimos cargar tu watchlist. Recarga la página para reintentar.
            </div>
          ) : rows.length === 0 ? (
            <EmptyState />
          ) : (
            <ul className="space-y-2">
              {rows.map((row, i) => (
                <Reveal key={row.id} delay={i * 50}>
                  <WatchlistRowItem row={row} />
                </Reveal>
              ))}
            </ul>
          )}
        </div>

        {/* Side column: account alert prefs */}
        <aside>
          <AlertPrefsPanel />
        </aside>
      </div>
    </div>
  );
}
