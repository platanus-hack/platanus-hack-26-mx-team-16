import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { getRefreshTokenFromRequest } from "@/src/application/helpers/session";
import {
  COOKIE_ACCESS_TOKEN,
  COOKIE_REFRESH_ATTEMPTS,
  COOKIE_REFRESH_TOKEN,
  MAX_REFRESH_ATTEMPTS,
  REFRESH_ATTEMPTS_MAX_AGE,
} from "@/src/constants";
import { Settings } from "@/src/settings";

const PUBLIC_EXACT_ROUTES = ["/", "/register", "/reset-password"];
// Token-bearing public flows. Anything under these prefixes is reachable
// without auth so links sent by email keep working when the recipient
// is signed out.
const PUBLIC_PREFIX_ROUTES = ["/invitations/", "/reset-password/"];
const LOGIN_REDIRECT_PATH = "/dashboard";

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT_ROUTES.includes(pathname)) return true;
  return PUBLIC_PREFIX_ROUTES.some((p) => pathname.startsWith(p));
}

export const config = {
  matcher: [
    // All routes except static assets
    "/((?!_next/|_vercel|.*\\..*|icons/|config/|images/).*)",
    // Explicitly match API v1 routes for proxying
    "/api/v1/:path*",
  ],
};

export async function proxy(req: NextRequest) {
  const url = req.nextUrl;

  // ─── PROXY: forward /api/v1/* to backend ───
  if (url.pathname.startsWith("/api/v1/")) {
    const backendPath = url.pathname.replace(/^\/api/, "");
    const backendUrl = new URL(
      backendPath + url.search,
      process.env.BACKEND_API_HOST
    );

    const requestHeaders = new Headers(req.headers);
    requestHeaders.set("X-Api-Key", process.env.BACKEND_API_KEY!);

    if (process.env.CF_ACCESS_CLIENT_ID) {
      requestHeaders.set(
        "CF-Access-Client-Id",
        process.env.CF_ACCESS_CLIENT_ID
      );
    }
    if (process.env.CF_ACCESS_CLIENT_SECRET) {
      requestHeaders.set(
        "CF-Access-Client-Secret",
        process.env.CF_ACCESS_CLIENT_SECRET
      );
    }

    return NextResponse.rewrite(backendUrl, {
      request: { headers: requestHeaders },
    });
  }

  // ─── SKIP: internal API routes handle their own auth ───
  if (url.pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // ─── AUTH REDIRECTS ───
  const refreshToken = getRefreshTokenFromRequest(req);
  const isPublic = isPublicPath(url.pathname);

  // Authenticated user on public route -> would normally redirect to dashboard.
  // But if the user keeps bouncing back to a public route, the RT is broken
  // (revoked / signing secret rotated). Count attempts and bail after MAX_REFRESH_ATTEMPTS.
  if (refreshToken && isPublic) {
    const attempts = readAttempts(req);

    if (attempts >= MAX_REFRESH_ATTEMPTS) {
      // Loop detected. Clear the session so the user lands on login cleanly.
      const res = NextResponse.next();
      clearSessionCookies(res);
      return res;
    }

    const res = NextResponse.redirect(new URL(LOGIN_REDIRECT_PATH, req.url));
    res.cookies.set({
      name: COOKIE_REFRESH_ATTEMPTS,
      value: String(attempts + 1),
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_ATTEMPTS_MAX_AGE,
    });
    return res;
  }

  // Unauthenticated user on protected route -> redirect to login
  if (!refreshToken && !isPublic) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
}

function readAttempts(req: NextRequest): number {
  const raw = req.cookies.get(COOKIE_REFRESH_ATTEMPTS)?.value;
  if (!raw) return 0;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function clearSessionCookies(res: NextResponse): void {
  for (const name of [
    COOKIE_REFRESH_TOKEN,
    COOKIE_ACCESS_TOKEN,
    COOKIE_REFRESH_ATTEMPTS,
  ]) {
    res.cookies.set({
      name,
      value: "",
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
}
