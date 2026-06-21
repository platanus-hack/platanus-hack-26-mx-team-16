/**
 * Server-only loader for the Hall of Shame initial page (§F4). RSC anonymous
 * surfaces may call `backendGet` directly (see CLAUDE.md BFF note) instead of
 * round-tripping through `/api/owliver/ranking`. We forward `GET /v1/ranking`
 * worst-first, validate the rows with the zod schema, and fall back to the
 * fixture when the backend is unreachable so `/` renders from hour 2.
 *
 * INVARIANT: the server order is authoritative — we NEVER re-sort here.
 */
import "server-only";

import { rankingFixture } from "@/src/application/owliver/fixtures";
import { backendGet } from "@/src/application/owliver/lib/bff";
import { parsePage } from "@/src/application/owliver/lib/envelope";
import { type RankingRow, rankingRowSchema } from "@/src/application/owliver/schemas/api";

export type RankingPage = {
  rows: RankingRow[];
  nextCursor: string | null;
  /** True when we served fixtures (no live backend). */
  fromFixture: boolean;
};

export async function loadRankingPage(
  country = "mx"
): Promise<RankingPage> {
  const result = await backendGet("/ranking", { country });

  if (result.ok) {
    try {
      const { data, pagination } = parsePage(rankingRowSchema, result.data);
      return { rows: data, nextCursor: pagination.nextCursor, fromFixture: false };
    } catch {
      // Malformed payload — fall through to the fixture so the page still paints.
    }
  }

  return {
    rows: rankingFixture,
    nextCursor: null,
    fromFixture: true,
  };
}
