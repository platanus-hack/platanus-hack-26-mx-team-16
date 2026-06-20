export interface LoginResponse {
  ok: boolean;
  error?: string;
  redirect?: string;
}

export async function login(
  email: string,
  password: string,
  redirect?: string,
): Promise<LoginResponse> {
  const formData = new FormData();
  formData.append('email', email);
  formData.append('password', password);
  if (redirect) formData.append('redirect', redirect);

  const response = await fetch('/api/auth/login', {
    method: 'POST',
    body: formData,
  });

  if (response.redirected) {
    window.location.href = response.url;
    return { ok: true };
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    return { ok: false, error: data.error || 'Login failed' };
  }

  const data = await response.json();
  if (data.redirect) {
    window.location.href = data.redirect;
  }
  return { ok: true, redirect: data.redirect };
}

export async function logout(redirect = '/login'): Promise<void> {
  const response = await fetch('/api/auth/logout', { method: 'POST' });
  if (response.redirected) {
    window.location.href = response.url;
  } else {
    window.location.href = redirect;
  }
}
