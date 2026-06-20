import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E6 · W8 · BFF staff: métricas QA/aprobaciones (solo `staff_admin` — el
 * backend responde 403 para el resto; se refleja tal cual).
 *
 * GET /api/staff/metrics?tenant=&since=
 *   → GET {backend}/staff/v1/metrics
 *
 * Reenvía SOLO Authorization — jamás X-Tenant (la superficie staff es
 * cross-tenant).
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const params: Record<string, string> = {};
  for (const key of ["tenant", "since"]) {
    const value = searchParams.get(key);
    if (value) params[key] = value;
  }

  try {
    const response = await staffServerHttp.get("/metrics", {
      params,
      headers: staffBackendHeadersFrom(request),
    });
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
