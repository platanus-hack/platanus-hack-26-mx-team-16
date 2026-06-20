import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF staff: claim/release de una tarea L1 (lock pesimista).
 *
 * POST /api/staff/tasks/{taskId}/claim  body `{ release?: boolean }`
 *   → POST {backend}/staff/v1/tasks/{taskId}/claim
 *
 * El 409 `human_task.already_claimed` se refleja tal cual (holder en el
 * mensaje) para que la UI muestre quién tiene el lock.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  try {
    const response = await staffServerHttp.post(
      `/tasks/${taskId}/claim`,
      { release: Boolean(body.release) },
      { headers: staffBackendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
