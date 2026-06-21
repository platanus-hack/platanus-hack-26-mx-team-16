/**
 * HeroScanDemo — the landing centerpiece: a self-running miniature of an Owliver
 * audit, composed from the *real* product parts (OwlMascot, Gauge, GradeBadge,
 * FindingFeedItem, ToolChips) rather than a hand-drawn illustration. It cycles
 * through the genuine product states — scanning → detection → grade — so the
 * motion reports state (DESIGN.md §6), not decoration.
 *
 * Reduced motion: settles immediately on the graded final frame (no beam, no
 * cycling); every child also honors prefers-reduced-motion on its own.
 */
"use client";

import Image from "next/image";
import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";
import type { Severity } from "@/src/application/owliver/schemas/api";
import { FindingFeedItem } from "@/src/presentation/owliver/components/finding-feed-item";
import { Gauge } from "@/src/presentation/owliver/components/gauge";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

type Phase = "scanning" | "graded";

const TARGET = "banco-ejemplo.gob.mx";
const SCORE = 58;

const TOOLS: { name: string; kind: "web" | "agentic" }[] = [
  { name: "nuclei", kind: "web" },
  { name: "zap", kind: "web" },
  { name: "testssl", kind: "web" },
  { name: "garak", kind: "agentic" },
  { name: "promptfoo", kind: "agentic" },
];

const FINDINGS: {
  severity: Severity;
  title: string;
  category: string;
  source: "owasp" | "agentic";
}[] = [
  {
    severity: "critical",
    title: "Prompt-injection en el chatbot de soporte",
    category: "LLM01",
    source: "agentic",
  },
  {
    severity: "high",
    title: "Sin CSP ni cabeceras de seguridad",
    category: "A05",
    source: "owasp",
  },
];

export function HeroScanDemo({ className }: { className?: string }) {
  const reduced = useReducedMotion();
  const [phase, setPhase] = React.useState<Phase>("graded");

  // Cycle scanning → graded → hold → repeat, unless reduced motion is on.
  React.useEffect(() => {
    if (reduced) {
      setPhase("graded");
      return;
    }
    let toGraded: ReturnType<typeof setTimeout>;
    let toRestart: ReturnType<typeof setTimeout>;
    const run = () => {
      setPhase("scanning");
      toGraded = setTimeout(() => setPhase("graded"), 3200);
      toRestart = setTimeout(run, 6600);
    };
    run();
    return () => {
      clearTimeout(toGraded);
      clearTimeout(toRestart);
    };
  }, [reduced]);

  const graded = phase === "graded";

  return (
    <div className={cn("relative", className)}>
      {/* Soft ambient halo — tonal depth behind the panel, no hard ring. */}
      <div
        aria-hidden
        className="absolute -inset-8 -z-10 rounded-[2rem] bg-[radial-gradient(circle_at_70%_18%,color-mix(in_oklab,var(--tertiary)_30%,transparent),transparent_34%),radial-gradient(circle_at_10%_85%,color-mix(in_oklab,var(--secondary)_18%,transparent),transparent_32%)] blur-2xl"
      />

      <div
        role="img"
        aria-label={`Demostración: Owliver audita ${TARGET} y obtiene el grado E`}
        className="overflow-hidden rounded-[1.75rem] border border-outline-variant bg-surface-container-lowest p-3 shadow-[0_4px_10px_rgba(40,30,8,0.14)]"
      >
        {/* Browser chrome bar */}
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-1 pb-3">
          <div className="flex gap-1.5" aria-hidden>
            <span className="size-2.5 rounded-full bg-grade-e" />
            <span className="size-2.5 rounded-full bg-grade-c" />
            <span className="size-2.5 rounded-full bg-grade-a" />
          </div>
          <div className="flex min-w-0 flex-1 items-center gap-2 rounded-full bg-surface-container px-3 py-1.5">
            <span className="size-1.5 shrink-0 rounded-full bg-secondary" />
            <span className="truncate font-mono text-xs text-on-surface-variant">
              {TARGET}
            </span>
          </div>
          <div className="relative grid size-9 place-items-center rounded-full bg-primary-container">
            <Image
              src="/owliver-icon-1000.png"
              alt=""
              width={22}
              height={22}
              className="size-[22px] object-contain"
              aria-hidden
            />
            <OwlMascot
              state={graded ? "alert" : "running"}
              size={22}
              className="absolute inset-0 m-auto"
            />
          </div>
        </div>

        {/* Scan stage — site skeleton + sweeping violet beam + sonar ping. */}
        <div className="relative h-40 overflow-hidden rounded-2xl bg-[linear-gradient(135deg,var(--surface-container-high),var(--surface-container)),radial-gradient(circle_at_80%_20%,color-mix(in_oklab,var(--primary)_16%,transparent),transparent_30%)]">
          {/* Wireframe of the target being inspected */}
          <div className="absolute inset-0 flex flex-col gap-2.5 p-4 opacity-75">
            <div className="h-4 w-36 rounded-full bg-surface-container-highest" />
            <div className="h-2.5 w-[78%] rounded-full bg-outline-variant/80" />
            <div className="h-2.5 w-[56%] rounded-full bg-outline-variant/80" />
            <div className="mt-auto flex gap-2">
              <div className="h-7 w-24 rounded-xl bg-primary/22" />
              <div className="h-7 w-16 rounded-xl bg-surface-container-highest" />
            </div>
          </div>

          {/* Sonar ping at the inspection point */}
          <div className="absolute right-5 top-5 grid place-items-center">
            <span
              className={cn(
                "absolute size-10 rounded-full bg-primary/30",
                !reduced && phase === "scanning" && "animate-sonar-ping"
              )}
            />
            <span className="size-2.5 rounded-full bg-primary shadow-[0_0_0_4px_color-mix(in_oklab,var(--primary)_22%,transparent)]" />
          </div>

          {/* Sweeping scan beam (height is a fraction of the box → resolution-free) */}
          {!reduced && phase === "scanning" && (
            <div
              aria-hidden
              className="animate-scan-beam absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-transparent via-primary/45 to-transparent"
            />
          )}

          {/* Status pill */}
          <div className="absolute left-3 top-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container-lowest/90 px-2.5 py-1 font-mono text-[11px] font-semibold tracking-wide text-on-surface-variant shadow-xs backdrop-blur">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  graded ? "bg-grade-e" : "bg-primary"
                )}
              />
              {graded ? "GRADO LISTO" : "ESCANEANDO…"}
            </span>
          </div>
        </div>

        {/* Tool chips — ignite in sequence while scanning, settle to ok when graded */}
        <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-5">
          {TOOLS.map((tool, i) => {
            const accent = tool.kind === "agentic" ? "tertiary" : "primary";
            return (
              <span
                key={tool.name}
                className="inline-flex min-h-7 items-center justify-center gap-1.5 rounded-full bg-surface-container-low px-2.5 py-1 font-mono text-[11px] text-on-surface-variant"
              >
                <span
                  className="size-1.5 rounded-full transition-colors duration-300"
                  style={{
                    transitionDelay: reduced ? "0ms" : `${i * 240}ms`,
                    backgroundColor: graded
                      ? "var(--grade-a)"
                      : `var(--${accent})`,
                  }}
                />
                {tool.name}
              </span>
            );
          })}
        </div>

        {/* Results — gauge counts up + findings spring in on grading */}
        <div className="mt-3 grid min-h-36 grid-cols-1 items-stretch gap-3 sm:grid-cols-[8.5rem_1fr]">
          <div className="grid place-items-center rounded-2xl bg-surface-container-low px-2 py-2">
            <Gauge
              score={graded ? SCORE : null}
              grade={graded ? "E" : null}
              size={112}
              label="Global"
              emptyHint="auditando…"
            />
          </div>

          <div className="flex min-h-[7.5rem] flex-col justify-center gap-2">
            {graded ? (
              <>
                <div className="flex items-center gap-2.5 px-0.5">
                  <GradeBadge grade="E" size="sm" />
                  <span className="text-sm font-medium text-foreground">
                    2 hallazgos que importan
                  </span>
                </div>
                {FINDINGS.map((f, i) => (
                  <FindingFeedItem
                    key={f.category}
                    severity={f.severity}
                    title={f.title}
                    category={f.category}
                    source={f.source}
                    live={!reduced}
                    delay={i * 140}
                  />
                ))}
              </>
            ) : (
              <div className="flex flex-col gap-2" aria-hidden>
                <div className="h-12 animate-pulse rounded-xl bg-surface-container-low" />
                <div className="h-12 animate-pulse rounded-xl bg-surface-container-low [animation-delay:200ms]" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
