import { type NextRequest, NextResponse } from "next/server";

import {
  mirrorBackendError,
  staffBackendHeadersFrom,
} from "@/src/infrastructure/http/bff";
import { staffServerHttp } from "@/src/infrastructure/http/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * E5 · BFF staff: resolver una tarea L1 (señala el run pausado).
 *
 * POST /api/staff/tasks/{taskId}/resolve  body `{ resolution: {...} }`
 *   → POST {backend}/staff/v1/tasks/{taskId}/resolve
 *
 * El 409 `human_task.open_flags` (campos flageados sin verificar) se
 * refleja tal cual para que la UI abra el force-dialog con la lista.
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
      `/tasks/${taskId}/resolve`,
      { resolution: body.resolution ?? {} },
      { headers: staffBackendHeadersFrom(request) }
    );
    return NextResponse.json(response.data, { status: response.status });
  } catch (error) {
    return mirrorBackendError(error);
  }
}
