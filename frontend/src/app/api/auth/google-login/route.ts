import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_TOKEN_MAX_AGE,
  COOKIE_ACCESS_TOKEN,
  COOKIE_REFRESH_ATTEMPTS,
  COOKIE_REFRESH_TOKEN,
  REFRESH_TOKEN_MAX_AGE,
} from "@/src/constants";
import { genericServerError } from "@/src/domain/errors/common";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { Settings } from "@/src/settings";

import { PENDING_DEST_COOKIE } from "../google/start/route";

const authRepository = new HttpAuthRepository(serverHttp);

const DEFAULT_DEST = "/watcher";

/** Only allow same-site relative paths as the post-login destination. */
function safeNext(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (!raw.startsWith("/") || raw.startsWith("//")) return null;
  return raw;
}

/**
 * Google OAuth — STEP 2 (exchange). The `/login/callback` client component POSTs
 * the `code` Google returned here; this server route forwards it to the
 * boilerplate backend `/auth/google-login` (which talks to Google + mints our
 * session), then sets the HttpOnly access/refresh cookies exactly like the
 * password login route. It also resolves the post-login `redirect` from the
 * `next` body field or the pending-destination cookie set in STEP 1 (§F10:
 * "redirect a la watchlist o al destino pendiente"), defaulting to /watchlist.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const code: string | undefined = body?.code;

    if (!code) {
      return NextResponse.json(
        { errors: [{ code: "code_required", message: "Falta el código de Google" }] },
        { status: 400 }
      );
    }

    const result = await authRepository.googleLogin(code);
    if (isErrorFeedback(result)) {
      return NextResponse.json(result, { status: 401 });
    }

    const { session, user, tenant, tenantRole } = result.data;

    const redirectTo =
      safeNext(body?.next) ??
      safeNext(request.cookies.get(PENDING_DEST_COOKIE)?.value) ??
      DEFAULT_DEST;

    const response = NextResponse.json({
      data: { user, tenant, tenantRole, redirect: redirectTo },
      datetime: result.datetime,
    });

    response.cookies.set({
      name: COOKIE_ACCESS_TOKEN,
      value: session.accessToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_TOKEN_MAX_AGE,
    });

    response.cookies.set({
      name: COOKIE_REFRESH_TOKEN,
      value: session.refreshToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_TOKEN_MAX_AGE,
    });

    // Reset the refresh-attempts loop counter on successful auth.
    response.cookies.set({
      name: COOKIE_REFRESH_ATTEMPTS,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });

    // Consume the pending-destination cookie now that it's been resolved.
    response.cookies.set({
      name: PENDING_DEST_COOKIE,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });

    return response;
  } catch (error) {
    console.error("Error en google-login:", error);
    return NextResponse.json(genericServerError, { status: 500 });
  }
}
