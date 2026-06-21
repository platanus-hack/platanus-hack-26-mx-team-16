/**
 * BFF: GET /api/owliver/scans/{id} → backend GET /v1/scans/{id} (§F6).
 * Initial theater state (status, progress, scores, tools_status, visibility).
 * 404 for a private scan without permission is forwarded verbatim (the backend
 * does NOT confirm existence). Fixture fallback returns the demo scan.
 */
import { type NextRequest, NextResponse } from "next/server";

import { scanFixture } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await backendGet(`/scans/${id}`);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 404) {
    return NextResponse.json(result.error, { status: 404 });
  }
  return NextResponse.json(asData(scanFixture));
}
