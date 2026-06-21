/**
 * BFF: GET /api/owliver/ranking → backend GET /v1/ranking (08-ranking).
 * Worst-first, cursor-paginated. The browser hits this same-origin route; we
 * forward via `backendGet` with the X-Api-Key + session cookie. When the backend
 * is unreachable (no live API yet) we fall back to the ranking FIXTURE so the
 * leaderboard renders from hour 2 (§F15).
 */
import { type NextRequest, NextResponse } from "next/server";

import { rankingFixture } from "@/src/application/owliver/fixtures";
import { asPage } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const country = searchParams.get("country") ?? "mx";
  const grade = searchParams.get("grade");
  const worst = searchParams.get("worst");
  const cursor = searchParams.get("cursor");
  const limit = searchParams.get("limit");

  const params: Record<string, string> = { country };
  if (grade) params.grade = grade;
  if (worst) params.worst = worst;
  if (cursor) params.cursor = cursor;
  if (limit) params.limit = limit;

  const result = await backendGet("/ranking", params);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }

  // Fixture fallback (offline / pre-backend). Honor simple client filters so the
  // demo behaves like the live path (which forwards both `grade` and `worst`).
  let rows = rankingFixture;
  if (grade) rows = rows.filter((r) => r.overallGrade === grade);
  if (worst === "web" || worst === "agentic") {
    // "Worst dimension" = the row's failing side. Grades run A (best) → F (worst),
    // so the worse dimension is the one with the higher letter. Keep rows where the
    // selected dimension exists and is at least as bad as the other (or the other
    // is absent).
    const rank = (g: string | null | undefined): number =>
      g ? g.charCodeAt(0) : -1;
    rows = rows.filter((r) => {
      const sel = worst === "web" ? r.webGrade : r.agenticGrade;
      const other = worst === "web" ? r.agenticGrade : r.webGrade;
      return rank(sel) >= 0 && rank(sel) >= rank(other);
    });
  }
  return NextResponse.json(asPage(rows, { nextCursor: null, limit: rows.length }));
}
