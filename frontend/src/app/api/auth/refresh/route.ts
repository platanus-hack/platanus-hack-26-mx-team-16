import { cookies } from "next/headers";
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
  invalidRefreshToken,
} from "@/src/domain/errors/common";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { Settings } from "@/src/settings";

const authRepository = new HttpAuthRepository(serverHttp);

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();

    // Obtener refresh token de las cookies
    const refreshToken = cookieStore.get(COOKIE_REFRESH_TOKEN)?.value;

    if (!refreshToken) {
      return clearSessionResponse(NextResponse.json(invalidRefreshToken, { status: 401 }));
    }

    // Llamar al repositorio para refrescar el token
    const result = await authRepository.refresh(refreshToken);

    // Si hay error, retornar error y limpiar la sesión: si el backend rechaza
    // el RT no tiene sentido seguir guardándolo en el navegador.
    if (isErrorFeedback(result)) {
      return clearSessionResponse(NextResponse.json(result, { status: 401 }));
    }

    // Si es exitoso, establecer nuevas cookies y retornar access token
    const { session, user, tenant, tenantRole } = result.data;

    const response = NextResponse.json({
      accessToken: session.accessToken,
      data: {
        user,
        tenant,
        tenantRole,
      },
      datetime: result.datetime,
    });

    // Configurar cookies HTTP-only
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

    // Refresh Token - 7 días (renovar también el refresh token)
    response.cookies.set({
      name: COOKIE_REFRESH_TOKEN,
      value: session.refreshToken,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_TOKEN_MAX_AGE,
    });

    // Reset the refresh-attempts loop counter on successful refresh.
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
    console.error("Error en refresh:", error);
    return NextResponse.json(genericServerError, { status: 500 });
  }
}

function clearSessionResponse(response: NextResponse): NextResponse {
  for (const name of [
    COOKIE_REFRESH_TOKEN,
    COOKIE_ACCESS_TOKEN,
    COOKIE_REFRESH_ATTEMPTS,
  ]) {
    response.cookies.set({
      name,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}
