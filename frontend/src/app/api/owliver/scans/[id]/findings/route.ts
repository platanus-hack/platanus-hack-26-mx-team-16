/**
 * BFF: GET /api/owliver/scans/{id}/findings → backend GET /v1/scans/{id}/findings
 * (§F7, cursor-paginated). Fixture fallback returns the SAT demo findings.
 */
import { type NextRequest, NextResponse } from "next/server";

import { findingsFixture } from "@/src/application/owliver/fixtures";
import { asPage } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const cursor = searchParams.get("cursor");

  const result = await backendGet(
    `/scans/${id}/findings`,
    cursor ? { cursor } : undefined
  );

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 404) {
    return NextResponse.json(result.error, { status: 404 });
  }
  return NextResponse.json(asPage(findingsFixture, { nextCursor: null }));
}
