/**
 * AddDomainForm (§F11) — add a domain to the watchlist. Client-side URL
 * normalization (`extractHost` + `isLikelyPublicHost`) mirrors the scan form:
 * rejects private/localhost/dotless hosts before hitting the BFF. A `monitor`
 * Switch decides whether periodic re-scans start immediately. Errors from the
 * mutation surface inline.
 */
"use client";

import * as React from "react";
import { Loader2, Plus } from "lucide-react";

import { useAddWatchlist } from "@/src/application/owliver/hooks/use-watchlist";
import {
  extractHost,
  isLikelyPublicHost,
} from "@/src/application/owliver/lib/url";
import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";

export function AddDomainForm({ onAdded }: { onAdded?: () => void }) {
  const add = useAddWatchlist();
  const [url, setUrl] = React.useState("");
  const [monitor, setMonitor] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const host = extractHost(url);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!url.trim()) {
      setError("Ingresa una URL o dominio.");
      return;
    }
    if (!isLikelyPublicHost(url)) {
      setError("Ingresa un dominio público válido (no IPs privadas ni localhost).");
      return;
    }
    try {
      await add.mutateAsync({ url, monitor });
      setUrl("");
      setMonitor(true);
      onAdded?.();
    } catch {
      setError("No se pudo agregar el dominio. Verifica tu sesión e inténtalo de nuevo.");
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-outline-variant bg-card p-5 shadow-xs"
    >
      <label
        htmlFor="watchlist-url"
        className="text-sm font-medium text-foreground"
      >
        Agregar dominio
      </label>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          id="watchlist-url"
          type="text"
          inputMode="url"
          autoComplete="off"
          placeholder="ejemplo.com.mx"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-invalid={error ? true : undefined}
          className="h-10 flex-1 rounded-xl border border-outline bg-background px-3 font-mono text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <label className="flex items-center gap-2 whitespace-nowrap">
          <span className="text-sm text-on-surface-variant">Monitorear</span>
          <Switch checked={monitor} onCheckedChange={setMonitor} />
        </label>
        <Button type="submit" variant="tertiary" disabled={add.isPending}>
          {add.isPending ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="size-4" aria-hidden />
          )}
          Agregar
        </Button>
      </div>
      {host && !error && (
        <p className="mt-2 text-xs text-on-surface-variant">
          Vas a vigilar:{" "}
          <span className="font-mono text-foreground">{host}</span>
        </p>
      )}
      {error && (
        <p className="mt-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
