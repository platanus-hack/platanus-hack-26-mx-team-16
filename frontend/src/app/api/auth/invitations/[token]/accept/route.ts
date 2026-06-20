import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_TOKEN_MAX_AGE,
  COOKIE_ACCESS_TOKEN,
  COOKIE_REFRESH_ATTEMPTS,
  COOKIE_REFRESH_TOKEN,
  REFRESH_TOKEN_MAX_AGE,
} from "@/src/constants";
import { genericServerError } from "@/src/domain/errors/common";
import { serverHttp } from "@/src/infrastructure/http/client";
import { Settings } from "@/src/settings";

interface AcceptBody {
  firstName?: string | null;
  lastName?: string | null;
  password?: string;
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ token: string }> },
) {
  const { token } = await context.params;
  try {
    const body = (await request.json()) as AcceptBody;
    const backendRes = await serverHttp.post(
      `/invitations/${encodeURIComponent(token)}/accept`,
      body,
      { validateStatus: () => true },
    );
    if (backendRes.status >= 400) {
      return NextResponse.json(backendRes.data, { status: backendRes.status });
    }

    const { session, user, tenant, tenantRole } = backendRes.data.data;
    const response = NextResponse.json({
      data: { user, tenant, tenantRole },
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
    console.error("Error en accept-invitation:", error);
    return NextResponse.json(genericServerError, { status: 500 });
  }
}
