/**
 * BFF: POST /api/owliver/scans/{id}/share → backend POST /v1/scans/{id}/share
 * (§F7). Returns { token } for a `/r/{token}` public link (TTL 7 days). Fixture
 * fallback mints a demo token so the share toast works offline.
 */
import { type NextRequest, NextResponse } from "next/server";

import { asData } from "@/src/application/owliver/lib/envelope";
import { backendPost } from "@/src/application/owliver/lib/bff";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const result = await backendPost(`/scans/${id}/share`);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  if (result.status === 403) {
    return NextResponse.json(result.error, { status: 403 });
  }
  return NextResponse.json(
    asData({
      token: `demo-${id}`,
      expiresAt: new Date(Date.now() + 7 * 86_400_000).toISOString(),
    })
  );
}
