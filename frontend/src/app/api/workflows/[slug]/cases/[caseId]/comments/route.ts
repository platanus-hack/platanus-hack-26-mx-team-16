import { type NextRequest, NextResponse } from "next/server";

import {
  backendHeadersFrom,
  mirrorBackendError,
} from "@/src/infrastructure/http/bff";
import { serverHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF: comentario del caso (handoff L1→L2 / notas del analista).
 *
 * POST /api/workflows/{slug}/cases/{caseId}/comments
 *   → POST {backend}/v1/workflows/{slug}/cases/{caseId}/comments
 *
 * Body: `{ body: string }`. Responde 201 con el shape exacto del timeline
 * (`{uuid, type, payload, actor, createdAt}`) para insertarlo tal cual.
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
      `/workflows/${slug}/cases/${caseId}/comments`,
      { body: String(body.body ?? "") },
      { headers: backendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
