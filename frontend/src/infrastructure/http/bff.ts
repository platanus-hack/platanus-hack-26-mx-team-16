import type { AxiosError } from "axios";
import { type NextRequest, NextResponse } from "next/server";

import { Settings } from "@/src/settings";

/**
 * Helpers compartidos por las BFF routes (`src/app/api/.../route.ts`).
 *
 * El cliente llama a la BFF con sus headers de sesión (Authorization +
 * X-Tenant, adjuntados por `attachAuthHeaders`); aquí los reenviamos al
 * backend junto con la X-Api-Key server-only — el mismo contrato que aplica
 * el proxy de `/api/v1/*` (src/proxy.ts).
 */
export function backendHeadersFrom(
  request: NextRequest
): Record<string, string> {
  const headers: Record<string, string> = {};

  const auth = request.headers.get("authorization");
  if (auth) headers.Authorization = auth;

  const tenant = request.headers.get("x-tenant");
  if (tenant) headers["X-Tenant"] = tenant;

  if (Settings.apiKey) headers["X-Api-Key"] = Settings.apiKey;

  if (process.env.CF_ACCESS_CLIENT_ID) {
    headers["CF-Access-Client-Id"] = process.env.CF_ACCESS_CLIENT_ID;
  }
  if (process.env.CF_ACCESS_CLIENT_SECRET) {
    headers["CF-Access-Client-Secret"] = process.env.CF_ACCESS_CLIENT_SECRET;
  }

  return headers;
}

/**
 * E5 · ADR 0001 — headers para la superficie staff (`/staff/v1/*`).
 *
 * Reenvía SOLO `Authorization` (el JWT con claim `is_staff` gatea en el
 * backend). JAMÁS `X-Tenant`: la consola staff es cross-tenant y el backend
 * rechaza el header con 400. Tampoco `X-Api-Key` (ese es el plano M2M).
 */
export function staffBackendHeadersFrom(
  request: NextRequest
): Record<string, string> {
  const headers: Record<string, string> = {};

  const auth = request.headers.get("authorization");
  if (auth) headers.Authorization = auth;

  if (process.env.CF_ACCESS_CLIENT_ID) {
    headers["CF-Access-Client-Id"] = process.env.CF_ACCESS_CLIENT_ID;
  }
  if (process.env.CF_ACCESS_CLIENT_SECRET) {
    headers["CF-Access-Client-Secret"] = process.env.CF_ACCESS_CLIENT_SECRET;
  }

  return headers;
}

/**
 * Refleja la respuesta de error del backend tal cual (status + payload),
 * para que el cliente vea exactamente el envelope de errores del API
 * (p. ej. 409 `case.not_complete` con la lista de faltantes).
 */
export function mirrorBackendError(error: unknown): NextResponse {
  const axiosError = error as AxiosError;
  if (axiosError?.response) {
    const data = axiosError.response.data ?? {
      errors: [
        { code: "bff.upstream_error", message: "Error del servicio backend" },
      ],
      validation: null,
    };
    return NextResponse.json(data, { status: axiosError.response.status });
  }
  return NextResponse.json(
    {
      errors: [
        {
          code: "bff.upstream_unreachable",
          message: "No se pudo contactar al backend",
        },
      ],
      validation: null,
    },
    { status: 502 }
  );
}
