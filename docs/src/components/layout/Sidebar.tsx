import { useEffect, useState } from 'react';

interface SidebarProps {
  section: 'docs' | 'guides' | 'api';
  currentSlug?: string;
}

interface NavGroup {
  label: string;
  items: { slug: string; title: string; badge?: string }[];
}

const NAV: Record<SidebarProps['section'], NavGroup[]> = {
  docs: [
    {
      label: 'Getting Started',
      items: [
        { slug: 'introduction', title: 'Introduction' },
        { slug: 'quickstart', title: 'Quickstart' },
        { slug: 'architecture', title: 'Architecture' },
      ],
    },
    {
      label: 'Backend',
      items: [
        { slug: 'backend/modules', title: 'Modules' },
        { slug: 'backend/use-cases', title: 'Use Cases' },
        { slug: 'backend/repositories', title: 'Repositories' },
        { slug: 'backend/events', title: 'Events & SSE' },
      ],
    },
    {
      label: 'Frontend',
      items: [
        { slug: 'frontend/structure', title: 'Project Structure' },
        { slug: 'frontend/bff', title: 'BFF Pattern' },
        { slug: 'frontend/components', title: 'Components' },
      ],
    },
    {
      label: 'Operations',
      items: [
        { slug: 'operations/deployment', title: 'Deployment' },
        { slug: 'operations/monitoring', title: 'Monitoring' },
        { slug: 'operations/secrets', title: 'Secrets' },
      ],
    },
  ],
  guides: [
    {
      label: 'Tutorials',
      items: [
        { slug: 'add-a-use-case', title: 'Add a Use Case', badge: 'beginner' },
        { slug: 'add-an-sse-endpoint', title: 'Add an SSE Endpoint', badge: 'intermediate' },
        { slug: 'add-a-bff-route', title: 'Add a BFF Route', badge: 'beginner' },
        { slug: 'add-a-design-token', title: 'Add a Design Token', badge: 'beginner' },
      ],
    },
    {
      label: 'Recipes',
      items: [
        { slug: 'multi-tenant', title: 'Multi-tenant Setup' },
        { slug: 'temporal-workflow', title: 'Temporal Workflows' },
        { slug: 'knowledge-base', title: 'Knowledge Base & RAG' },
      ],
    },
  ],
  api: [
    {
      label: 'Auth',
      items: [
        { slug: 'auth/login', title: 'POST /auth/login' },
        { slug: 'auth/refresh', title: 'POST /auth/refresh' },
        { slug: 'auth/me', title: 'GET /auth/me' },
      ],
    },
    {
      label: 'Documents',
      items: [
        { slug: 'documents/upload', title: 'POST /documents/upload' },
        { slug: 'documents/list', title: 'GET /documents' },
        { slug: 'documents/get', title: 'GET /documents/{id}' },
      ],
    },
    {
      label: 'Extraction',
      items: [
        { slug: 'extraction/run', title: 'POST /extraction/run' },
        { slug: 'extraction/status', title: 'GET /extraction/{id}' },
      ],
    },
    {
      label: 'Webhooks',
      items: [
        { slug: 'webhooks/extraction-completed', title: 'extraction.completed' },
        { slug: 'webhooks/extraction-failed', title: 'extraction.failed' },
      ],
    },
  ],
};

export function Sidebar({ section, currentSlug = '' }: SidebarProps) {
  const [activeSlug, setActiveSlug] = useState(currentSlug);

  useEffect(() => {
    if (currentSlug) setActiveSlug(currentSlug);
  }, [currentSlug]);

  const groups = NAV[section] || [];

  return (
    <nav className="px-4 py-6">
      <p
        className="mb-3 px-2 font-mono text-[10px] uppercase tracking-wider"
        style={{ color: 'var(--color-fg-subtle)' }}
      >
        {section}
      </p>
      <div className="space-y-6">
        {groups.map((group) => (
          <div key={group.label}>
            <p
              className="mb-2 px-2 text-xs font-semibold"
              style={{ color: 'var(--color-fg)' }}
            >
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = activeSlug === item.slug;
                return (
                  <li key={item.slug}>
                    <a
                      href={`/${section}/${item.slug}`}
                      className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition"
                      style={{
                        backgroundColor: isActive
                          ? 'var(--color-primary-subtle)'
                          : 'transparent',
                        color: isActive
                          ? 'var(--color-primary-hover)'
                          : 'var(--color-fg-muted)',
                        fontWeight: isActive ? 500 : 400,
                      }}
                    >
                      <span>{item.title}</span>
                      {item.badge && (
                        <span
                          className="rounded px-1.5 py-0.5 font-mono text-[9px] uppercase"
                          style={{
                            backgroundColor: 'var(--color-bg-subtle)',
                            color: 'var(--color-fg-subtle)',
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
