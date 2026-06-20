import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useSessionStore } from "@/src/application/contexts/session-store";
import { getCommonHeaders } from "@/src/infrastructure/requests";
import { Settings } from "@/src/settings";

// ─── Server-side: direct to backend (used by API routes) ───
export const serverHttp = axios.create({
  baseURL: `${Settings.apiBaseUrl}/v1`,
  timeout: 10000,
});

// ─── Client-side: via Next.js API routes (/api/auth/*) ───
export const localHttp = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

// ─── Shared interceptor logic ───

function attachAuthHeaders(config: InternalAxiosRequestConfig) {
  const { tenant, accessToken } = useSessionStore.getState();
  const common = getCommonHeaders(tenant?.slug ?? null, accessToken ?? null);

  config.headers = config.headers || {};

  if (typeof config.headers.set === "function") {
    for (const [k, v] of Object.entries(common)) {
      if (v == null) continue;
      config.headers.set(k, v);
    }
  } else {
    Object.assign(config.headers, common);
  }
  return config;
}

// ─── Refresh token deduplication ───

let refreshPromise: Promise<string | null> | null = null;
let isRedirecting = false;

function deduplicatedRefresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccess().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function refreshAccess(): Promise<string | null> {
  try {
    const res = await axios.post("/api/auth/refresh", null, {
      withCredentials: true,
    });
    return res.data?.accessToken ?? null;
  } catch {
    return null;
  }
}

function handleRefreshFailure(): void {
  if (isRedirecting) return;
  isRedirecting = true;
  useSessionStore.getState().clearSession();
  if (typeof window !== "undefined") {
    window.location.href = "/";
  }
}

function createRefreshInterceptor(httpClient: ReturnType<typeof axios.create>) {
  return async (error: AxiosError) => {
    const original: InternalAxiosRequestConfig & { _retry?: boolean } =
      error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    const status = error.response?.status;
    const errorCode = (error.response?.data as any)?.errors?.[0]?.code;
    const isAuthError =
      status === 401 ||
      (status === 403 && errorCode === "auth.NotAuthenticated");
    if (isAuthError && !original?._retry && !isRedirecting) {
      original._retry = true;

      const newToken = await deduplicatedRefresh();

      if (newToken) {
        useSessionStore.getState().setAccessToken(newToken);
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return httpClient(original);
      }

      handleRefreshFailure();
    }

    return Promise.reject(error);
  };
}

// ─── Apply interceptors to client-side instances ───

localHttp.interceptors.request.use(attachAuthHeaders);
localHttp.interceptors.response.use(
  (r) => r,
  createRefreshInterceptor(localHttp)
);

// ─── Client-side: via proxy for all domain API calls (/api/v1/*) ───
export const authHttp = axios.create({
  baseURL: "/api",
});

authHttp.interceptors.request.use(attachAuthHeaders);
authHttp.interceptors.response.use(
  (r) => r,
  createRefreshInterceptor(authHttp)
);
