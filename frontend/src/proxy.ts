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

const PUBLIC_EXACT_ROUTES = [
  "/", // public landing — "Cómo funciona" (the leaderboard moved to /watch, gated)
  "/register",
  "/reset-password",
  "/login",
  "/scan", // scan form (basic level is anonymous)
];
// Token-bearing / anonymous public flows. Anything under these prefixes is
// reachable without auth so links sent by email keep working when the recipient
// is signed out, and so Owliver's viral surfaces (reports, sites, live theater)
// are anonymous. Per-scan AuthZ is decided by the backend via `visibility`.
const PUBLIC_PREFIX_ROUTES = [
  "/invitations/",
  "/reset-password/",
  "/login/", // Google OAuth callback (`/login/callback`) — anon until cookie set

  "/scans/", // live theater + report (backend gates by visibility → 404)
  "/sites/", // site history (anonymous)
  "/r/", // public redacted report (token)
];
const LOGIN_REDIRECT_PATH = "/dashboard";
// Where unauthenticated users are sent when hitting a protected route.
const LOGIN_PATH = "/login";

// Auth-entry routes: a signed-in user landing here is bounced to the app
// (they don't need to log in again). Owliver's anonymous content surfaces
// (landing `/`, `/scan`, reports, sites) are public but NOT auth-entry —
// a signed-in user can browse them freely without being redirected away.
const AUTH_ENTRY_ROUTES = ["/login", "/register", "/reset-password"];

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT_ROUTES.includes(pathname)) return true;
  return PUBLIC_PREFIX_ROUTES.some((p) => pathname.startsWith(p));
}

function isAuthEntryPath(pathname: string): boolean {
  return (
    AUTH_ENTRY_ROUTES.includes(pathname) ||
    pathname.startsWith("/reset-password/")
  );
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

  // Authenticated user on an AUTH-ENTRY route (login/register/reset) -> redirect
  // to the app. Owliver's anonymous content routes (landing `/`, `/scan`, reports…)
  // are public but NOT auth-entry, so a signed-in user browses them without a bounce.
  // If the user keeps bouncing back, the RT is broken (revoked / secret rotated):
  // count attempts and bail after MAX_REFRESH_ATTEMPTS.
  if (refreshToken && isAuthEntryPath(url.pathname)) {
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
    return NextResponse.redirect(new URL(LOGIN_PATH, req.url));
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
