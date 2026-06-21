/**
 * `useRanking` — the leaderboard, cursor-paginated (§F4). The
 * server already returns rows WORST-FIRST (grade F first, penaltyRaw DESC); the
 * client NEVER re-sorts. Filters (grade / worst-dimension / country) are passed
 * through to the BFF as query params.
 *
 * Reads via `fetch("/api/owliver/ranking", …)` (same-origin BFF). The initial
 * page can also be rendered as RSC server-side; this hook powers "cargar más"
 * and client-side filtering.
 */
"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import {
  type PageEnvelope,
  parsePage,
} from "../lib/envelope";
import { type RankingRow, rankingRowSchema } from "../schemas/api";
import { owliverKeys } from "./query-keys";

export type RankingFilters = {
  country?: string;
  /** Filter by exact overall grade. */
  grade?: string;
  /** Filter by worst dimension. */
  worst?: "web" | "agentic";
  limit?: number;
};

async function fetchRankingPage(
  filters: RankingFilters,
  cursor: string | null
): Promise<{ data: RankingRow[]; nextCursor: string | null }> {
  const params = new URLSearchParams();
  params.set("country", filters.country ?? "mx");
  if (filters.grade) params.set("grade", filters.grade);
  if (filters.worst) params.set("worst", filters.worst);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (cursor) params.set("cursor", cursor);

  const res = await fetch(`/api/owliver/ranking?${params.toString()}`, {
    credentials: "same-origin",
  });
  if (!res.ok) throw new Error(`ranking ${res.status}`);
  const body = (await res.json()) as PageEnvelope<unknown>;
  const { data, pagination } = parsePage(rankingRowSchema, body);
  return { data, nextCursor: pagination.nextCursor };
}

export function useRanking(filters: RankingFilters = {}) {
  return useInfiniteQuery({
    queryKey: owliverKeys.ranking(filters.country ?? "mx", filters),
    queryFn: ({ pageParam }) =>
      fetchRankingPage(filters, pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.nextCursor,
  });
}
