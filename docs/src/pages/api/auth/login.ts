import type { APIRoute } from 'astro';
import {
  loginRequest,
  setSessionCookies,
  type AuthError,
} from '@/lib/auth/server';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  const formData = await request.formData();
  const email = formData.get('email')?.toString();
  const password = formData.get('password')?.toString();
  const redirectTo = formData.get('redirect')?.toString() || '/';

  if (!email || !password) {
    return new Response(
      JSON.stringify({ error: 'Email and password are required' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    );
  }

  try {
    const tokens = await loginRequest(email, password);

    const mockContext = {
      url: new URL(request.url),
      cookies,
    } as Parameters<typeof setSessionCookies>[0];

    setSessionCookies(mockContext, tokens);

    return redirect(redirectTo, 303);
  } catch (error) {
    const authError = error as AuthError;
    return new Response(
      JSON.stringify({
        error: authError.message || 'Invalid credentials',
      }),
      {
        status: authError.status || 401,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  }
};
