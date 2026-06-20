import { useEffect, useState } from 'react';

interface Heading {
  slug: string;
  text: string;
  depth: number;
}

interface TableOfContentsProps {
  headings: Heading[];
}

export function TableOfContents({ headings }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: '-80px 0px -80% 0px' },
    );

    headings.forEach((h) => {
      const el = document.getElementById(h.slug);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [headings]);

  if (headings.length === 0) return null;

  return (
    <nav>
      <p
        className="mb-3 font-mono text-[10px] uppercase tracking-wider"
        style={{ color: 'var(--color-fg-subtle)' }}
      >
        On this page
      </p>
      <ul className="space-y-1.5 border-l" style={{ borderColor: 'var(--color-border)' }}>
        {headings.map((h) => (
          <li
            key={h.slug}
            style={{ paddingLeft: `${(h.depth - 2) * 12 + 12}px` }}
          >
            <a
              href={`#${h.slug}`}
              className="block text-xs leading-snug transition"
              style={{
                color:
                  activeId === h.slug
                    ? 'var(--color-primary)'
                    : 'var(--color-fg-muted)',
                fontWeight: activeId === h.slug ? 600 : 400,
                borderLeft:
                  activeId === h.slug
                    ? '2px solid var(--color-primary)'
                    : '2px solid transparent',
                marginLeft: '-1px',
                paddingLeft: '8px',
              }}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
