import type { APIRoute } from 'astro';
import { getSession } from '@/lib/auth/server';

export const GET: APIRoute = async (context) => {
  const session = await getSession(context);

  if (!session) {
    return new Response(JSON.stringify({ authenticated: false }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(
    JSON.stringify({
      authenticated: true,
      user: {
        id: session.userId,
        email: session.email,
        name: session.name,
        role: session.role,
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
};
