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
  invalidCredentials,
} from "@/src/domain/errors/common";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { Settings } from "@/src/settings";

const authRepository = new HttpAuthRepository(serverHttp);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      return NextResponse.json(invalidCredentials, { status: 400 });
    }

    const result = await authRepository.login(email, password);
    if (isErrorFeedback(result)) {
      return NextResponse.json(result, { status: 401 });
    }

    const { session, user, tenant, tenantRole } = result.data;
    const response = NextResponse.json({
      data: {
        user,
        tenant,
        tenantRole,
      },
      datetime: result.datetime,
    });

    // Access Token - 10 minutos
    response.cookies.set({
      name: COOKIE_ACCESS_TOKEN,
      value: session.accessToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_TOKEN_MAX_AGE,
    });

    // Refresh Token - 7 días
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

    return response;
  } catch (error) {
    console.error("Error en login:", error);
    return NextResponse.json(genericServerError, { status: 500 });
  }
}
