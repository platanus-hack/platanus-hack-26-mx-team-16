import { defineMiddleware } from 'astro:middleware';
import {
  getSession,
  refreshRequest,
  setSessionCookies,
} from '@/lib/auth/server';

const PUBLIC_PATHS = ['/login/', '/login', '/api/auth/login', '/api/auth/refresh'];
const PUBLIC_PREFIXES = ['/_astro', '/_image', '/favicon', '/assets'];

export const onRequest = defineMiddleware(async (context, next) => {
  const { url, cookies, redirect } = context;
  const pathname = url.pathname;

  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return next();
  }

  const isPublic = PUBLIC_PATHS.some((path) => pathname === path);

  if (pathname === '/api/auth/session' || pathname === '/api/auth/session/') {
    return next();
  }

  let session = await getSession(context);

  if (!isPublic && !session) {
    const refreshToken = cookies.get('doxiq_docs_refresh')?.value;

    if (refreshToken) {
      try {
        const tokens = await refreshRequest(refreshToken);
        setSessionCookies(context, tokens);
        session = await getSession(context);
      } catch {
        // refresh failed, will redirect to login
      }
    }

    if (!session) {
      if (pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return redirect(`/login/?redirect=${encodeURIComponent(pathname)}`, 302);
    }

    context.locals.session = session;
  } else if (session) {
    context.locals.session = session;

    if (pathname === '/login' || pathname === '/login/') {
      return redirect('/', 302);
    }
  }

  return next();
});
