/**
 * BFF: POST /api/owliver/scans/{id}/cancel → backend POST /v1/scans/{id}/cancel
 * (§F6). Kills a running scan; the backend then emits a terminal `done`
 * {outcome:'cancelled'} on the stream. Fixture fallback acknowledges so the UI
 * can show "escaneo cancelado".
 */
import { type NextRequest, NextResponse } from "next/server";

import { asData } from "@/src/application/owliver/lib/envelope";
import { backendPost } from "@/src/application/owliver/lib/bff";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await backendPost(`/scans/${id}/cancel`);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 404) {
    return NextResponse.json(result.error, { status: 404 });
  }
  return NextResponse.json(asData({ scanId: id, outcome: "cancelled" }));
}
