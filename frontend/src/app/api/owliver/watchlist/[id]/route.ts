/**
 * BFF: PATCH/DELETE /api/owliver/watchlist/{id} → backend /v1/watchlist/{id}
 * (§F11, protected). `{id}` is the watchlist-ROW uuid (NEVER siteId).
 *  - PATCH  → toggle { monitor }.
 *  - DELETE → remove the row.
 */
import { type NextRequest, NextResponse } from "next/server";

import { backendRequest } from "@/src/application/owliver/lib/bff";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const result = await backendRequest({
    method: "PATCH",
    url: `/watchlist/${id}`,
    data: body,
  });
  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  return NextResponse.json(result.error, { status: result.status });
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await backendRequest({
    method: "DELETE",
    url: `/watchlist/${id}`,
  });
  if (result.ok) {
    return NextResponse.json(result.data ?? { id }, { status: result.status });
  }
  return NextResponse.json(result.error, { status: result.status });
}
