import { useState } from 'react';
import { login } from '@/lib/auth/client';

interface LoginFormProps {
  redirect?: string;
}

export function LoginForm({ redirect = '/' }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await login(email, password, redirect);
      if (!result.ok) {
        setError(result.error || 'Login failed');
        setIsLoading(false);
      }
    } catch (err) {
      setError('An unexpected error occurred');
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <label
          htmlFor="email"
          className="block text-sm font-medium"
          style={{ color: 'var(--color-fg)' }}
        >
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isLoading}
          className="w-full rounded-md border bg-white px-3 py-2.5 text-sm transition focus:outline-none focus:ring-2 disabled:opacity-50"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-fg)',
          }}
          placeholder="you@company.com"
        />
      </div>

      <div className="space-y-2">
        <label
          htmlFor="password"
          className="block text-sm font-medium"
          style={{ color: 'var(--color-fg)' }}
        >
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isLoading}
          className="w-full rounded-md border bg-white px-3 py-2.5 text-sm transition focus:outline-none focus:ring-2 disabled:opacity-50"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-fg)',
          }}
          placeholder="••••••••"
        />
      </div>

      {error && (
        <div
          className="rounded-md border px-3 py-2 text-sm"
          style={{
            backgroundColor: 'var(--color-danger)',
            borderColor: 'var(--color-danger)',
            color: 'white',
            opacity: 0.9,
          }}
        >
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50"
        style={{
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-primary-fg)',
        }}
      >
        {isLoading ? (
          <>
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                strokeOpacity="0.3"
              />
              <path
                d="M12 2a10 10 0 0 1 10 10"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
            Signing in...
          </>
        ) : (
          <>
            Sign in
            <span aria-hidden="true">→</span>
          </>
        )}
      </button>
    </form>
  );
}
