import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF staff: agregado read-only del caso para la tarea en mano.
 *
 * GET /api/staff/cases/{caseId}
 *   → GET {backend}/staff/v1/cases/{caseId}
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await params;

  try {
    const response = await staffServerHttp.get(`/cases/${caseId}`, {
      headers: staffBackendHeadersFrom(request),
    });
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
