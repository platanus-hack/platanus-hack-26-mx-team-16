import { type NextRequest, NextResponse } from "next/server";

import {
  backendHeadersFrom,
  mirrorBackendError,
} from "@/src/infrastructure/http/bff";
import { serverHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF: verificación por campo del Inspection Bench.
 *
 * PATCH /api/workflows/{slug}/cases/{caseId}/documents/{documentId}/fields
 *   → PATCH {backend}/v1/workflows/.../documents/{documentId}/fields
 *
 * Body: `{ fieldPath, action: "correct"|"accept", value? }` o lista. El
 * backend decamela las claves (middleware), así que el body viaja tal cual.
 * Errores espejados: 423 `case.locked` (holder), 503 si la señal
 * `corrections` al run pausado falla, 404 binding workflow→caso→doc.
 */
export async function PATCH(
  request: NextRequest,
  {
    params,
  }: {
    params: Promise<{ slug: string; caseId: string; documentId: string }>;
  }
) {
  const { slug, caseId, documentId } = await params;

  let body: unknown = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  try {
    const response = await serverHttp.patch(
      `/workflows/${slug}/cases/${caseId}/documents/${documentId}/fields`,
      body,
      { headers: backendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
