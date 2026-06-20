import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { COOKIE_ACCESS_TOKEN, COOKIE_REFRESH_TOKEN } from "@/src/constants";
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
    const result = await authRepository.logout(refreshToken);

    // Crear respuesta
    const response = NextResponse.json({
      data: {
        status: "SUCCESS",
      },
      datetime: new Date().toISOString(),
    });

    // Eliminar cookies
    response.cookies.set({
      name: COOKIE_ACCESS_TOKEN,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });

    response.cookies.set({
      name: COOKIE_REFRESH_TOKEN,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });

    return response;
  } catch (error) {
    console.error("Error en logout:", error);
    return NextResponse.json(
      {
        errors: [
          {
            code: "SERVER_ERROR",
            message: "Error al cerrar sesión",
          },
        ],
        validation: null,
      },
      { status: 500 }
    );
  }
}
