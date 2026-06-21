/**
 * BFF: GET /api/r/{token} → backend GET /v1/r/{token} (§F8). Public redacted
 * report by share token — NO login. Status is preserved verbatim: 404 (missing),
 * 410 (expired/revoked), 200 (redacted report with raw evidence stripped
 * server-side). Fixture fallback (offline) returns the redacted demo report so a
 * shared link always renders.
 */
import { type NextRequest, NextResponse } from "next/server";

import { publicReportFixture } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  const result = await backendGet(`/r/${token}`);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 404) {
    return NextResponse.json(result.error, { status: 404 });
  }
  if (result.status === 410) {
    return NextResponse.json(result.error, { status: 410 });
  }
  return NextResponse.json(asData(publicReportFixture));
}
