import type { AxiosError } from "axios";
import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_TOKEN_MAX_AGE,
  COOKIE_ACCESS_TOKEN,
  COOKIE_REFRESH_ATTEMPTS,
  COOKIE_REFRESH_TOKEN,
  REFRESH_TOKEN_MAX_AGE,
} from "@/src/constants";
import {
  genericServerError,
  refreshCookieNotFound,
} from "@/src/domain/errors/common";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { getCommonHeaders } from "@/src/infrastructure/requests";
import { Settings } from "@/src/settings";
import { handleHttpError } from "@/src/utils/http-error-handler";

const authRepository = new HttpAuthRepository(serverHttp);

const nameRequired = {
  errors: [
    { code: "tenants.NameRequired", message: "Tenant name is required." },
  ],
  validation: null,
};

function setAuthCookies(
  response: NextResponse,
  accessToken: string,
  refreshToken: string
) {
  // Access Token - 10 minutos
  response.cookies.set({
    name: COOKIE_ACCESS_TOKEN,
    value: accessToken,
    httpOnly: true,
    secure: Settings.isProd,
    sameSite: "lax",
    path: "/",
    maxAge: ACCESS_TOKEN_MAX_AGE,
  });

  // Refresh Token - 7 días
  response.cookies.set({
    name: COOKIE_REFRESH_TOKEN,
    value: refreshToken,
    httpOnly: true,
    secure: Settings.isProd,
    sameSite: "lax",
    path: "/",
    maxAge: REFRESH_TOKEN_MAX_AGE,
  });

  // Reset the refresh-attempts loop counter.
  response.cookies.set({
    name: COOKIE_REFRESH_ATTEMPTS,
    value: "",
    httpOnly: true,
    secure: Settings.isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}

/**
 * BFF: create the caller's first tenant. The authenticated user becomes its
 * owner — the backend sets `is_owner=true` and the user's `current_tenant_id`
 * synchronously — so re-issuing the session afterwards returns the new tenant.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => null);
    const name = typeof body?.name === "string" ? body.name.trim() : "";
    const countryCode =
      typeof body?.countryCode === "string" && body.countryCode
        ? body.countryCode
        : "MX";

    if (!name) {
      return NextResponse.json(nameRequired, { status: 400 });
    }

    const refreshToken = request.cookies.get(COOKIE_REFRESH_TOKEN)?.value;
    if (!refreshToken) {
      return NextResponse.json(refreshCookieNotFound, { status: 401 });
    }

    // 1. Mint a fresh access token — the one in the cookie may have expired
    //    while the user was filling in the form.
    const refreshed = await authRepository.refresh(refreshToken);
    if (isErrorFeedback(refreshed)) {
      return NextResponse.json(refreshed, { status: 401 });
    }

    // 2. Create the tenant (caller becomes owner).
    try {
      await serverHttp.post(
        "/tenants",
        { name, country_code: countryCode },
        { headers: getCommonHeaders(null, refreshed.data.session.accessToken) }
      );
    } catch (error) {
      const axiosError = error as AxiosError;
      const status = axiosError.response?.status ?? 500;
      return NextResponse.json(handleHttpError(axiosError), { status });
    }

    // 3. Re-issue the session, now resolved against the freshly created tenant.
    const session = await authRepository.refresh(
      refreshed.data.session.refreshToken
    );
    if (isErrorFeedback(session)) {
      return NextResponse.json(session, { status: 401 });
    }

    const { session: jwt, user, tenant, tenantRole } = session.data;
    const response = NextResponse.json({
      data: { user, tenant, tenantRole },
      datetime: session.datetime,
    });
    setAuthCookies(response, jwt.accessToken, jwt.refreshToken);
    return response;
  } catch (error) {
    console.error("Error creating tenant:", error);
    return NextResponse.json(genericServerError, { status: 500 });
  }
}
