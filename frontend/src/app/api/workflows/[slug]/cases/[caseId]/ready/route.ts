import { type NextRequest, NextResponse } from "next/server";

import {
  backendHeadersFrom,
  mirrorBackendError,
} from "@/src/infrastructure/http/bff";
import { serverHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E4 · BFF: marcar un caso como listo.
 *
 * POST /api/workflows/{slug}/cases/{caseId}/ready
 *   → POST {backend}/v1/workflows/{slug}/cases/{caseId}/ready
 *
 * Body: `{ force?: boolean }`. El 409 `case.not_complete` (faltantes y
 * !force) se refleja tal cual para que el cliente abra el dialog de
 * confirmación con la lista de faltantes. Si el shape real difiere al
 * integrar, este route handler es el único punto de mapping a ajustar.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string; caseId: string }> }
) {
  const { slug, caseId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  try {
    const response = await serverHttp.post(
      `/workflows/${slug}/cases/${caseId}/ready`,
      { force: Boolean(body.force) },
      { headers: backendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
