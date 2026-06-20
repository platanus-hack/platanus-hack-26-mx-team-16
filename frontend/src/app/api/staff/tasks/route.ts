import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF staff (ADR 0001): cola L1 unificada cross-tenant.
 *
 * GET /api/staff/tasks?tenant=&status=&kind=&limit=
 *   → GET {backend}/staff/v1/tasks
 *
 * `kind=qa|approval` segmenta la cola (E6 §3). Reenvía SOLO Authorization —
 * jamás X-Tenant (400 en backend).
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const params: Record<string, string> = {};
  for (const key of ["tenant", "status", "kind", "limit"]) {
    const value = searchParams.get(key);
    if (value) params[key] = value;
  }

  try {
    const response = await staffServerHttp.get("/tasks", {
      params,
      headers: staffBackendHeadersFrom(request),
    });
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
