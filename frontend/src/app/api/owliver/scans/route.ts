/**
 * BFF: POST /api/owliver/scans → backend POST /v1/scans (§F5, 12-api).
 * Body { url, level, authorized }. Returns { scanId } (201 new / 200 idempotent).
 * Propagates 422 (attestation/validation) and 429 (Retry-After) verbatim so the
 * form can map them to UI. Fixture fallback returns the SAT demo scan id.
 */
import { type NextRequest, NextResponse } from "next/server";

import { SAT_SCAN_ID } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendPost } from "@/src/application/owliver/lib/bff";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const result = await backendPost("/scans", body);

  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }

  // Surface real validation/attestation/rate-limit errors to the form.
  if ([422, 429, 403].includes(result.status)) {
    return NextResponse.json(result.error, { status: result.status });
  }

  // Fixture fallback: hand back the demo scan id so the flow continues.
  return NextResponse.json(asData({ scanId: SAT_SCAN_ID }), { status: 201 });
}
