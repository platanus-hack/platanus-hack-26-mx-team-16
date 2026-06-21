/**
 * `/watcher` — Watchlist workspace (§F11, PROTECTED). Merges the old
 * `/watchlist` (add domains, per-row monitor toggle, account alert prefs) with
 * the inspection-bench grade explainer brought over from `/watch`. One
 * customizable watchlist with two tabs:
 *   • Sitios — add form + watched rows, alongside the animated InspectionBench.
 *   • Config — account alert prefs (email + Slack webhook).
 *
 * Client component (state: editable name, tabs, add form, switches). The name
 * is persisted to localStorage (no backend field for it yet). Auth is gated by
 * the parent `(protected)` layout; all data flows through the BFF
 * (`/api/owliver/watchlist`, `/api/owliver/me/alerts`) with fixture fallback.
 */
"use client";

import * as React from "react";
import { Check, Eye, Pencil } from "lucide-react";

import { useWatchlist } from "@/src/application/owliver/hooks/use-watchlist";
import { Button } from "@/src/presentation/components/ui/button";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";
import { AddDomainForm } from "@/src/presentation/owliver/watchlist/add-domain-form";
import { AlertPrefsPanel } from "@/src/presentation/owliver/watchlist/alert-prefs-panel";
import { InspectionBench } from "@/src/presentation/owliver/watchlist/inspection-bench";
import { WatchlistRowItem } from "@/src/presentation/owliver/watchlist/watchlist-row-item";

const NAME_KEY = "owliver:watcher:name";
const DEFAULT_NAME = "Mi watchlist";

/** Editable, locally-persisted watchlist title. */
function WatchlistName() {
  const [name, setName] = React.useState(DEFAULT_NAME);
  const [draft, setDraft] = React.useState(DEFAULT_NAME);
  const [editing, setEditing] = React.useState(false);

  React.useEffect(() => {
    const stored = window.localStorage.getItem(NAME_KEY);
    if (stored) {
      setName(stored);
      setDraft(stored);
    }
  }, []);

  function save() {
    const next = draft.trim() || DEFAULT_NAME;
    setName(next);
    setDraft(next);
    setEditing(false);
    window.localStorage.setItem(NAME_KEY, next);
  }

  if (editing) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
        className="flex items-center gap-2"
      >
        <Eye className="size-6 shrink-0 text-primary" aria-hidden />
        <input
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setDraft(name);
              setEditing(false);
            }
          }}
          maxLength={48}
          aria-label="Nombre de la watchlist"
          className="min-w-0 flex-1 border-b border-outline bg-transparent text-2xl font-semibold tracking-tight text-foreground outline-none focus-visible:border-ring md:text-3xl"
        />
        <Button type="submit" size="icon-sm" variant="ghost" aria-label="Guardar nombre">
          <Check className="size-4" />
        </Button>
      </form>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Eye className="size-6 shrink-0 text-primary" aria-hidden />
      <h1 className="truncate text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
        {name}
      </h1>
      <button
        type="button"
        onClick={() => setEditing(true)}
        aria-label="Renombrar watchlist"
        className="rounded-full p-1.5 text-on-surface-variant outline-none transition-colors hover:bg-surface-container hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Pencil className="size-4" />
      </button>
    </div>
  );
}

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

export default function WatcherPage() {
  const { data, isLoading, isError } = useWatchlist();
  const rows = data ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:px-6">
      <header className="mb-8">
        <WatchlistName />
        <p className="mt-2 text-on-surface-variant">
          Vigila tus dominios y activa el monitoreo continuo. Los resultados de
          escaneos activos son privados de tu cuenta.
        </p>
      </header>

      <Tabs defaultValue="sitios">
        <TabsList aria-label="Secciones de la watchlist">
          <TabsTrigger
            value="sitios"
            className="data-[active]:bg-primary data-[active]:text-primary-foreground"
          >
            Sitios
          </TabsTrigger>
          <TabsTrigger
            value="config"
            className="data-[active]:bg-primary data-[active]:text-primary-foreground"
          >
            Config
          </TabsTrigger>
        </TabsList>

        {/* Sitios — add form + rows alongside the inspection bench */}
        <TabsContent value="sitios" className="mt-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
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
                  No pudimos cargar tu watchlist. Recarga la página para
                  reintentar.
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

            <aside className="lg:sticky lg:top-24 lg:self-start">
              <InspectionBench />
            </aside>
          </div>
        </TabsContent>

        {/* Config — account alert prefs (email + Slack) */}
        <TabsContent value="config" className="mt-6">
          <div className="max-w-xl">
            <AlertPrefsPanel />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
