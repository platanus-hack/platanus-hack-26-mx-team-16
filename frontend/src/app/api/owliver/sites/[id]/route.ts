/**
 * BFF: GET /api/owliver/sites/{id} → backend GET /v1/sites/{id} (§F9).
 * Site history (latest scan + grade timeline). Anonymous. Fixture fallback
 * returns the demo site so `/sites/[id]` renders without a backend.
 */
import { type NextRequest, NextResponse } from "next/server";

import { siteFixture } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await backendGet(`/sites/${id}`);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 404) {
    return NextResponse.json(result.error, { status: 404 });
  }
  return NextResponse.json(asData(siteFixture));
}
