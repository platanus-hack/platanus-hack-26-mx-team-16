import { type NextRequest, NextResponse } from "next/server";

import {
  backendHeadersFrom,
  mirrorBackendError,
} from "@/src/infrastructure/http/bff";
import { serverHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E4 · BFF: completitud del expediente (cálculo fresco).
 *
 * GET /api/workflows/{slug}/cases/{caseId}/completeness
 *   → GET {backend}/v1/workflows/{slug}/cases/{caseId}/completeness
 *
 * Devuelve `{ data: { satisfied, autoReady, readyAt, required, present,
 * missing } }`. Si el shape real difiere al integrar, este route handler
 * es el único punto de mapping a ajustar.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string; caseId: string }> }
) {
  const { slug, caseId } = await params;

  try {
    const response = await serverHttp.get(
      `/workflows/${slug}/cases/${caseId}/completeness`,
      { headers: backendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
