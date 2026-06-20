import type { APIContext } from 'astro';

const BACKEND_URL = import.meta.env.BACKEND_API_HOST || 'http://localhost:8200';
const AUTH_COOKIE = 'doxiq_docs_session';
const REFRESH_COOKIE = 'doxiq_docs_refresh';

export interface Session {
  userId: string;
  email: string;
  name: string;
  role: string;
  tenantId?: string;
  expiresAt: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

interface BackendSession {
  accessToken: string;
  refreshToken: string;
}

interface BackendUser {
  uuid: string;
  firstName?: string | null;
  lastName?: string | null;
  username?: string | null;
  emailAddress?: { email?: string | null } | null;
}

interface BackendTenant {
  uuid: string;
}

interface LoginPayload {
  session: BackendSession;
  user: BackendUser;
  tenant?: BackendTenant | null;
}

interface SessionPayload {
  user: BackendUser;
  tenant?: BackendTenant | null;
  tenantRole?: { name?: string | null } | null;
}

function extractTokens(payload: LoginPayload): AuthTokens {
  const accessToken = payload.session.accessToken;
  const refreshToken = payload.session.refreshToken;
  const decoded = decodeJwt(accessToken);

  return {
    accessToken,
    refreshToken,
    expiresIn: decoded?.exp ? Math.max(0, decoded.exp - Math.floor(Date.now() / 1000)) : 3600,
  };
}

function decodeJwt(token: string): { exp?: number } | null {
  const parts = token.split('.');
  if (parts.length !== 3) {
    return null;
  }
  try {
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(padded.padEnd(padded.length + ((4 - (padded.length % 4)) % 4), '='));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function toSession(payload: SessionPayload, expiresAt: number): Session {
  const fullName = [payload.user.firstName, payload.user.lastName]
    .filter(Boolean)
    .join(' ')
    .trim();

  return {
    userId: payload.user.uuid,
    email: payload.user.emailAddress?.email ?? '',
    name: fullName || payload.user.username || payload.user.emailAddress?.email || '',
    role: payload.tenantRole?.name ?? 'Member',
    tenantId: payload.tenant?.uuid,
    expiresAt,
  };
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<AuthTokens> {
  const response = await fetch(`${BACKEND_URL}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error?.detail;
    const message =
      (typeof detail === 'string' ? detail : detail?.message) || 'Invalid credentials';
    throw new AuthError(message, response.status);
  }

  const envelope = (await response.json()) as { data: LoginPayload };
  return extractTokens(envelope.data);
}

export async function refreshRequest(refreshToken: string): Promise<AuthTokens> {
  const response = await fetch(`${BACKEND_URL}/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });

  if (!response.ok) {
    throw new AuthError('Refresh failed', response.status);
  }

  const envelope = (await response.json()) as { data: LoginPayload };
  return extractTokens(envelope.data);
}

export async function fetchUser(token: string): Promise<Session | null> {
  const response = await fetch(`${BACKEND_URL}/v1/auth/session`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    return null;
  }

  const envelope = (await response.json()) as { data: SessionPayload };
  const decoded = decodeJwt(token);
  const expiresAt = decoded?.exp ? decoded.exp * 1000 : Date.now() + 3600 * 1000;
  return toSession(envelope.data, expiresAt);
}

export function setSessionCookies(
  context: APIContext,
  tokens: AuthTokens,
): void {
  const isSecure = context.url.protocol === 'https:';

  context.cookies.set(AUTH_COOKIE, tokens.accessToken, {
    httpOnly: true,
    secure: isSecure,
    sameSite: 'lax',
    path: '/',
    maxAge: tokens.expiresIn,
  });

  context.cookies.set(REFRESH_COOKIE, tokens.refreshToken, {
    httpOnly: true,
    secure: isSecure,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30,
  });
}

export function clearSessionCookies(context: APIContext): void {
  context.cookies.delete(AUTH_COOKIE, { path: '/' });
  context.cookies.delete(REFRESH_COOKIE, { path: '/' });
}

export function getAccessToken(context: APIContext): string | undefined {
  return context.cookies.get(AUTH_COOKIE)?.value;
}

export function getRefreshToken(context: APIContext): string | undefined {
  return context.cookies.get(REFRESH_COOKIE)?.value;
}

export async function getSession(
  context: APIContext,
): Promise<Session | null> {
  const token = getAccessToken(context);
  if (!token) {
    return null;
  }
  return fetchUser(token);
}

export class AuthError extends Error {
  constructor(
    message: string,
    public status: number = 401,
  ) {
    super(message);
    this.name = 'AuthError';
  }
}
