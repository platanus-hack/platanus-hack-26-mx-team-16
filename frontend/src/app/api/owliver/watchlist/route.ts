/**
 * BFF: GET/POST /api/owliver/watchlist → backend /v1/watchlist (§F11, protected).
 *  - GET  → list watched rows (row `id` = watchlist-row uuid, NEVER siteId).
 *  - POST → add a domain { url, monitor }.
 * Fixture fallback applies to GET so the watchlist renders offline; writes
 * forward errors verbatim (they need a real session).
 */
import { type NextRequest, NextResponse } from "next/server";

import { watchlistFixture } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendGet, backendPost } from "@/src/application/owliver/lib/bff";

export async function GET() {
  const result = await backendGet("/watchlist");
  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  return NextResponse.json(asData(watchlistFixture));
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const result = await backendPost("/watchlist", body);
  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  return NextResponse.json(result.error, { status: result.status });
}
