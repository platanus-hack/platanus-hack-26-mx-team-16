/**
 * Watchlist hooks (§F11) — list + add + monitor toggle + remove. Mutations key
 * off the watchlist-ROW id (never siteId). All traffic goes through the BFF.
 */
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type DataEnvelope, parseData } from "../lib/envelope";
import { type WatchlistRow, watchlistRowSchema } from "../schemas/api";
import { owliverKeys } from "./query-keys";

async function getWatchlist(): Promise<WatchlistRow[]> {
  const res = await fetch("/api/owliver/watchlist", {
    credentials: "same-origin",
  });
  if (!res.ok) throw new Error(`watchlist ${res.status}`);
  const body = (await res.json()) as DataEnvelope<unknown[]>;
  return (body.data ?? []).map((r) => watchlistRowSchema.parse(r));
}

export function useWatchlist() {
  return useQuery({
    queryKey: owliverKeys.watchlist(),
    queryFn: getWatchlist,
  });
}

export function useAddWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { url: string; monitor: boolean }) => {
      const res = await fetch("/api/owliver/watchlist", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`watchlist add ${res.status}`);
      return parseData(watchlistRowSchema, await res.json());
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: owliverKeys.watchlist() }),
  });
}

export function useToggleMonitor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, monitor }: { id: string; monitor: boolean }) => {
      const res = await fetch(`/api/owliver/watchlist/${id}`, {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ monitor }),
      });
      if (!res.ok) throw new Error(`watchlist patch ${res.status}`);
      return parseData(watchlistRowSchema, await res.json());
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: owliverKeys.watchlist() }),
  });
}

export function useRemoveWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`/api/owliver/watchlist/${id}`, {
        method: "DELETE",
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error(`watchlist delete ${res.status}`);
      return id;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: owliverKeys.watchlist() }),
  });
}
