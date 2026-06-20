import type { APIRoute } from 'astro';
import { clearSessionCookies } from '@/lib/auth/server';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  const formData = await request.request.clone().formData().catch(() => null);
  const redirectTo = formData?.get('redirect')?.toString() || '/login';

  const mockContext = {
    url: new URL(request.url),
    cookies,
  } as Parameters<typeof clearSessionCookies>[0];

  clearSessionCookies(mockContext);

  return redirect(redirectTo, 303);
};

export const GET: APIRoute = async ({ cookies, redirect }) => {
  const mockContext = {
    url: new URL('http://localhost'),
    cookies,
  } as Parameters<typeof clearSessionCookies>[0];

  clearSessionCookies(mockContext);
  return redirect('/login', 303);
};
