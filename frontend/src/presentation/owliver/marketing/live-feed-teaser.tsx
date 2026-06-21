/**
 * LiveFeedTeaser — a compact, self-running preview of the Live Pentest Theater
 * (§F6): findings stream into the feed one by one (spring-in via FindingFeedItem),
 * the agent-team header shows who's working, and the stream loops. Demonstrates
 * the "inspectable live work" principle on the marketing surface.
 *
 * Reduced motion: shows the full settled feed at once, no streaming.
 */
"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";
import type { Severity } from "@/src/application/owliver/schemas/api";
import { FindingFeedItem } from "@/src/presentation/owliver/components/finding-feed-item";

const STREAM: {
  severity: Severity;
  title: string;
  category: string;
  source: "owasp" | "agentic";
}[] = [
  {
    severity: "critical",
    title: "Jailbreak filtra el system prompt del asistente",
    category: "LLM07",
    source: "agentic",
  },
  {
    severity: "high",
    title: "Cookie de sesión sin flag Secure ni HttpOnly",
    category: "A05",
    source: "owasp",
  },
  {
    severity: "medium",
    title: "TLS 1.0/1.1 aún habilitado en el servidor",
    category: "A02",
    source: "owasp",
  },
  {
    severity: "high",
    title: "Inyección indirecta vía contenido recuperado (RAG)",
    category: "LLM01",
    source: "agentic",
  },
  {
    severity: "low",
    title: "Encabezado X-Powered-By revela el stack",
    category: "A05",
    source: "owasp",
  },
];

const AGENTS = ["Orquestador · Opus", "Web · Sonnet", "Agéntico · Sonnet"];

export function LiveFeedTeaser({ className }: { className?: string }) {
  const reduced = useReducedMotion();
  const [count, setCount] = React.useState(STREAM.length);
  const [cycle, setCycle] = React.useState(0);

  React.useEffect(() => {
    if (reduced) {
      setCount(STREAM.length);
      return;
    }
    setCount(1);
    const id = setInterval(() => {
      setCount((c) => {
        if (c >= STREAM.length) {
          setCycle((k) => k + 1);
          return 1;
        }
        return c + 1;
      });
    }, 1500);
    return () => clearInterval(id);
  }, [reduced]);

  const shown = STREAM.slice(0, count);

  return (
    <div
      className={cn(
        "rounded-3xl border border-outline-variant bg-surface-container-low p-3 shadow-sm",
        className
      )}
    >
      {/* Agent-team header */}
      <div className="flex items-center justify-between gap-3 px-2 pb-3 pt-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
          {AGENTS.map((a) => (
            <span
              key={a}
              className="inline-flex items-center gap-1.5 font-mono text-[11px] text-on-surface-variant"
            >
              <span
                className={cn(
                  "size-1.5 rounded-full bg-secondary",
                  !reduced && "animate-soft-float"
                )}
              />
              {a}
            </span>
          ))}
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-destructive/12 px-2.5 py-1 font-mono text-[11px] font-semibold text-destructive-deep">
          <span className="relative flex size-1.5">
            {!reduced && (
              <span className="absolute inline-flex size-full animate-sonar-ping rounded-full bg-destructive" />
            )}
            <span className="relative inline-flex size-1.5 rounded-full bg-destructive" />
          </span>
          EN VIVO
        </span>
      </div>

      {/* Streaming feed */}
      <div className="flex flex-col gap-2" aria-live="polite">
        {shown.map((f, i) => (
          <FindingFeedItem
            key={`${cycle}-${f.category}-${i}`}
            severity={f.severity}
            title={f.title}
            category={f.category}
            source={f.source}
            live={!reduced}
          />
        ))}
      </div>
    </div>
  );
}
