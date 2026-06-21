import { type NextRequest, NextResponse } from "next/server";

import { Settings } from "@/src/settings";

/**
 * Google OAuth — STEP 1 (start). Server-only kick-off for the boilerplate Google
 * login flow reused by Owliver (§F10). The "Entrar con Google" button on
 * `/login` is a same-origin link to this route so the Google `client_id` /
 * `redirect_uri` never ship in the client bundle (they are server-only env vars,
 * mirrored by the backend `GOOGLE_REDIRECT_URI`).
 *
 * It stashes the post-login destination in a short-lived HttpOnly cookie (the
 * "destino pendiente" — e.g. the active-scan form that triggered the login) and
 * 302-redirects to Google's consent screen with the authorization-code flow.
 * Google sends the user back to `redirect_uri` (our `/login/callback`) with a
 * `?code=`, which the callback exchanges via `/api/auth/google-login`.
 */
export const PENDING_DEST_COOKIE = "___OWL_NEXT___";

const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";

/** Only allow same-site relative paths as the post-login destination. */
function safeNext(raw: string | null): string | null {
  if (!raw) return null;
  if (!raw.startsWith("/") || raw.startsWith("//")) return null;
  return raw;
}

export function GET(request: NextRequest) {
  const { clientId, redirectUri } = Settings.google;

  if (!clientId || !redirectUri) {
    // Misconfigured environment — bounce back to login with an error flag so the
    // page can show the OAuth error state instead of a dead redirect.
    const back = new URL("/login", request.url);
    back.searchParams.set("error", "config");
    return NextResponse.redirect(back);
  }

  const next = safeNext(request.nextUrl.searchParams.get("next"));

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid email profile",
    access_type: "offline",
    include_granted_scopes: "true",
    prompt: "select_account",
  });

  const response = NextResponse.redirect(`${GOOGLE_AUTH_URL}?${params.toString()}`);

  if (next) {
    response.cookies.set({
      name: PENDING_DEST_COOKIE,
      value: next,
      httpOnly: true,
      secure: Settings.isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 10, // 10 min — long enough to complete the consent screen
    });
  } else {
    // Clear any stale pending destination from a previous attempt.
    response.cookies.set({
      name: PENDING_DEST_COOKIE,
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
