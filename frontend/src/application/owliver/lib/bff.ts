/**
 * BFF helpers (server-only) — the canonical way an Owliver `route.ts` or RSC
 * forwards to the backend. Mirrors the login route pattern: the browser hits
 * `/api/...` (same-origin), the server calls `serverHttp` (baseURL `/v1`) with
 * `X-Api-Key` (injected by `getCommonHeaders`) + the access-token cookie as a
 * Bearer header. The browser NEVER talks to the backend directly.
 *
 * Do NOT import this from a Client Component — it reads HttpOnly cookies.
 */
import "server-only";

import type { AxiosRequestConfig } from "axios";
import { cookies } from "next/headers";

import { COOKIE_ACCESS_TOKEN } from "@/src/constants";
import { serverHttp } from "@/src/infrastructure/http/client";
import { getCommonHeaders } from "@/src/infrastructure/requests";

import { asError, type ErrorEnvelope, isErrorEnvelope } from "./envelope";

/**
 * Build the server-side auth headers for a backend call: `X-Api-Key` +
 * `X-Client` (from `getCommonHeaders`) and, when present, the access-token
 * cookie as `Authorization: Bearer`. Public endpoints simply omit the Bearer.
 */
export async function backendHeaders(): Promise<Record<string, string>> {
  const store = await cookies();
  const accessToken = store.get(COOKIE_ACCESS_TOKEN)?.value ?? null;
  return getCommonHeaders(null, accessToken);
}

export type BackendResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: ErrorEnvelope };

/**
 * Forward a request to the backend through `serverHttp`, attaching auth headers
 * and normalizing failures into the canonical error envelope. `status` is always
 * preserved so the caller can map 404/410/422/403 → UI.
 */
export async function backendRequest<T = unknown>(
  config: AxiosRequestConfig
): Promise<BackendResult<T>> {
  try {
    const headers = await backendHeaders();
    const res = await serverHttp.request<T>({
      ...config,
      headers: { ...headers, ...(config.headers ?? {}) },
      // Don't throw on 4xx so we can map status → UI ourselves.
      validateStatus: () => true,
    });

    if (res.status >= 200 && res.status < 300) {
      return { ok: true, status: res.status, data: res.data };
    }

    const body = res.data as unknown;
    const error = isErrorEnvelope(body)
      ? body
      : asError([
          {
            code: `http_${res.status}`,
            message:
              (body as { message?: string })?.message ??
              "Error en la solicitud",
          },
        ]);
    return { ok: false, status: res.status, error };
  } catch (e) {
    return {
      ok: false,
      status: 500,
      error: asError([
        {
          code: "network_error",
          message: e instanceof Error ? e.message : "Error de red",
        },
      ]),
    };
  }
}

/** Convenience: GET. */
export function backendGet<T = unknown>(url: string, params?: object) {
  return backendRequest<T>({ method: "GET", url, params });
}

/** Convenience: POST. */
export function backendPost<T = unknown>(url: string, data?: unknown) {
  return backendRequest<T>({ method: "POST", url, data });
}
