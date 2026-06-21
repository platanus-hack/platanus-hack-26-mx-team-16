/**
 * BFF helpers (server-only) — the canonical way an Owliver `route.ts` or RSC
 * forwards to the backend. Mirrors the login route pattern: the browser hits
 * `/api/...` (same-origin), the server calls `serverHttp` (baseURL `/v1`) with
 * `X-Api-Key` (injected by `getCommonHeaders`) + the access-token cookie as a
 * Bearer header. The browser NEVER talks to the backend directly.
 *
 * The Owliver hooks call these routes with a raw `fetch` (not the `authHttp`
 * axios instance), so they don't get the client-side refresh interceptor in
 * `infrastructure/http/client.ts`. Because the access-token cookie only lives
 * ~10 min while the refresh token lasts 7 days, a user who sits on a page past
 * that window keeps a valid session but a dead `___AT5___` cookie — every BFF
 * write would then 403 with `auth.NotAuthenticated`. `backendRequest` therefore
 * mirrors that interceptor server-side: on an auth failure it spends the
 * refresh-token cookie for a fresh session, rotates the cookies, and retries
 * once. See `tryRefreshAccessToken`.
 *
 * Do NOT import this from a Client Component — it reads HttpOnly cookies.
 */
import "server-only";

import type { AxiosRequestConfig } from "axios";
import { cookies } from "next/headers";

import {
  ACCESS_TOKEN_MAX_AGE,
  COOKIE_ACCESS_TOKEN,
  COOKIE_REFRESH_TOKEN,
  REFRESH_TOKEN_MAX_AGE,
} from "@/src/constants";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { getCommonHeaders } from "@/src/infrastructure/requests";
import { Settings } from "@/src/settings";

import { asError, type ErrorEnvelope, isErrorEnvelope } from "./envelope";

const authRepository = new HttpAuthRepository(serverHttp);

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
 * Is this a "your access token is gone/expired" failure that a refresh could
 * fix? Mirrors the client interceptor: a bare 401, or a 403 whose first error
 * code is `auth.NotAuthenticated` (what the backend returns for a missing
 * Bearer). A 403 for any other reason (real AuthZ denial) is left untouched.
 */
function isAuthFailure(result: BackendResult<unknown>): boolean {
  if (result.ok) return false;
  if (result.status === 401) return true;
  return (
    result.status === 403 &&
    result.error.errors[0]?.code === "auth.NotAuthenticated"
  );
}

/**
 * Spend the refresh-token cookie for a fresh session, persist the rotated
 * AT/RT cookies, and return the new access token (or `null` when there is no
 * usable refresh token / the backend rejects it).
 *
 * Cookie mutation is only allowed inside Route Handlers and Server Actions; an
 * RSC caller (e.g. the public `scans/[id]` / `sites/[id]` pages) will throw on
 * `store.set`, so the write is best-effort — the returned token still
 * authenticates the retry for the current render.
 */
async function tryRefreshAccessToken(): Promise<string | null> {
  const store = await cookies();
  const refreshToken = store.get(COOKIE_REFRESH_TOKEN)?.value ?? null;
  if (!refreshToken) return null;

  const result = await authRepository.refresh(refreshToken);
  if (isErrorFeedback(result)) return null;

  const { session } = result.data;

  try {
    store.set({
      name: COOKIE_ACCESS_TOKEN,
      value: session.accessToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_TOKEN_MAX_AGE,
    });
    store.set({
      name: COOKIE_REFRESH_TOKEN,
      value: session.refreshToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_TOKEN_MAX_AGE,
    });
  } catch {
    // RSC context — cookies are read-only here. The retry below still uses the
    // fresh token in-memory; the cookie will be rotated on the next mutation.
  }

  return session.accessToken;
}

/**
 * Issue a single backend call and normalize the outcome into a `BackendResult`.
 * `overrideToken`, when set, replaces the cookie-derived Bearer (used by the
 * post-refresh retry, where the new token isn't readable from cookies yet).
 */
async function sendOnce<T>(
  config: AxiosRequestConfig,
  overrideToken?: string
): Promise<BackendResult<T>> {
  const headers = overrideToken
    ? getCommonHeaders(null, overrideToken)
    : await backendHeaders();

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
            (body as { message?: string })?.message ?? "Error en la solicitud",
        },
      ]);
  return { ok: false, status: res.status, error };
}

/**
 * Forward a request to the backend through `serverHttp`, attaching auth headers
 * and normalizing failures into the canonical error envelope. `status` is always
 * preserved so the caller can map 404/410/422/403 → UI. On an auth failure the
 * request is retried once with a freshly refreshed access token.
 */
export async function backendRequest<T = unknown>(
  config: AxiosRequestConfig
): Promise<BackendResult<T>> {
  try {
    const result = await sendOnce<T>(config);
    if (!isAuthFailure(result)) return result;

    // Access token missing/expired but the session may still be valid — refresh
    // from the refresh-token cookie and retry once before surfacing the error.
    const accessToken = await tryRefreshAccessToken();
    if (!accessToken) return result;

    return await sendOnce<T>(config, accessToken);
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
