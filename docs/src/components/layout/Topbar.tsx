import { useState } from 'react';
import { logout } from '@/lib/auth/client';

interface User {
  userId: string;
  email: string;
  name: string;
  role: string;
}

interface TopbarProps {
  user?: User;
}

export function Topbar({ user }: TopbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header
      className="sticky top-0 z-40 flex h-16 items-center justify-between border-b px-6 backdrop-blur"
      style={{
        backgroundColor: 'rgba(248, 250, 252, 0.8)',
        borderColor: 'var(--color-border)',
      }}
    >
      <div className="flex items-center gap-3">
        <a href="/" className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-md"
            style={{ backgroundColor: 'var(--color-primary)' }}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              className="h-5 w-5"
              style={{ color: 'white' }}
            >
              <path
                d="M4 6h16M4 12h16M4 18h10"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div>
            <p
              className="font-display text-sm font-semibold leading-tight"
              style={{ color: 'var(--color-fg)' }}
            >
              Doxiq Docs
            </p>
            <p
              className="font-mono text-[10px] uppercase tracking-wider leading-tight"
              style={{ color: 'var(--color-fg-subtle)' }}
            >
              v1.2 · internal
            </p>
          </div>
        </a>

        <nav className="ml-8 hidden items-center gap-1 md:flex">
          <a
            href="/"
            className="rounded-md px-3 py-1.5 text-sm font-medium transition"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            Overview
          </a>
          <a
            href="/docs"
            className="rounded-md px-3 py-1.5 text-sm font-medium transition"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            Docs
          </a>
          <a
            href="/guides"
            className="rounded-md px-3 py-1.5 text-sm font-medium transition"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            Guides
          </a>
          <a
            href="/api"
            className="rounded-md px-3 py-1.5 text-sm font-medium transition"
            style={{ color: 'var(--color-fg-muted)' }}
          >
            API
          </a>
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <a
          href="https://github.com/llamitai/doxiq"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md p-1.5 transition"
          style={{ color: 'var(--color-fg-muted)' }}
          aria-label="GitHub"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12Z" />
          </svg>
        </a>

        {user && (
          <div className="relative">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition"
              style={{
                borderColor: 'var(--color-border)',
                backgroundColor: 'var(--color-bg-elevated)',
                color: 'var(--color-fg)',
              }}
            >
              <div
                className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
                style={{
                  backgroundColor: 'var(--color-primary-subtle)',
                  color: 'var(--color-primary-hover)',
                }}
              >
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span className="hidden md:inline">{user.name}</span>
              <svg
                className="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {menuOpen && (
              <div
                className="absolute right-0 top-full mt-1 w-56 rounded-md border shadow-lg"
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  borderColor: 'var(--color-border)',
                }}
                onMouseLeave={() => setMenuOpen(false)}
              >
                <div
                  className="border-b px-3 py-2.5"
                  style={{ borderColor: 'var(--color-border)' }}
                >
                  <p
                    className="text-sm font-medium"
                    style={{ color: 'var(--color-fg)' }}
                  >
                    {user.name}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: 'var(--color-fg-muted)' }}
                  >
                    {user.email}
                  </p>
                  <p
                    className="mt-1 font-mono text-[10px] uppercase tracking-wider"
                    style={{ color: 'var(--color-fg-subtle)' }}
                  >
                    {user.role}
                  </p>
                </div>
                <button
                  onClick={() => logout('/login')}
                  className="w-full px-3 py-2 text-left text-sm transition"
                  style={{ color: 'var(--color-fg)' }}
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
