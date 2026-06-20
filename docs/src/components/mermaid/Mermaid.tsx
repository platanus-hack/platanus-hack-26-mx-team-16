import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidProps {
  chart: string;
  id?: string;
}

let mermaidInitialized = false;
let mermaidIdCounter = 0;

function initMermaid() {
  if (mermaidInitialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      primaryColor: '#ccfbf1',
      primaryTextColor: '#0f172a',
      primaryBorderColor: '#0d9488',
      lineColor: '#475569',
      secondaryColor: '#fef3c7',
      tertiaryColor: '#f1f5f9',
      background: '#ffffff',
      mainBkg: '#ffffff',
      secondBkg: '#f8fafc',
      tertiaryBkg: '#f1f5f9',
      fontFamily: 'Figtree, system-ui, sans-serif',
      fontSize: '13px',
      borderRadius: '8px',
    },
    flowchart: {
      curve: 'basis',
      padding: 16,
    },
  });
  mermaidInitialized = true;
}

export function Mermaid({ chart, id }: MermaidProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string>('');
  const chartId = id || `mermaid-${++mermaidIdCounter}`;

  useEffect(() => {
    initMermaid();

    const render = async () => {
      try {
        const result = await mermaid.render(chartId, chart);
        setSvg(result.svg);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to render diagram';
        setError(message);
      }
    };

    render();
  }, [chart, chartId]);

  if (error) {
    return (
      <div
        className="mermaid-container"
        style={{
          borderColor: 'var(--color-danger)',
          backgroundColor: 'rgba(239, 68, 68, 0.05)',
        }}
      >
        <p
          className="mb-2 font-mono text-xs font-semibold uppercase"
          style={{ color: 'var(--color-danger)' }}
        >
          Mermaid render error
        </p>
        <pre
          className="overflow-x-auto rounded p-3 text-xs"
          style={{
            backgroundColor: 'var(--color-bg-subtle)',
            color: 'var(--color-fg)',
          }}
        >
          {error}
        </pre>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="mermaid-container"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
