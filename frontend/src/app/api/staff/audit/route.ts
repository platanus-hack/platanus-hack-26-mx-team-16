import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF staff: audit log de accesos (solo `staff_admin` — el backend
 * responde 403 para el resto; se refleja tal cual).
 *
 * GET /api/staff/audit?staff_user_id=&tenant=&action=&limit=&offset=
 *   → GET {backend}/staff/v1/audit
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const params: Record<string, string> = {};
  for (const key of ["staff_user_id", "tenant", "action", "limit", "offset"]) {
    const value = searchParams.get(key);
    if (value) params[key] = value;
  }

  try {
    const response = await staffServerHttp.get("/audit", {
      params,
      headers: staffBackendHeadersFrom(request),
    });
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
