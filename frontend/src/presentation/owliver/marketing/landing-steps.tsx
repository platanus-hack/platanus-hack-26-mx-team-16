/**
 * LandingSteps — the 3-step flow (URL → agent team → grade) wired together by an
 * animated "violet signal" that traces the path between steps (DESIGN.md §6, the
 * signature inspection gesture). The connectors are SVG; the marching dashes
 * freeze to a clean static line under prefers-reduced-motion.
 */
"use client";

import { Award, Link as LinkIcon, Radar } from "lucide-react";
import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";

const STEPS = [
  {
    icon: LinkIcon,
    title: "Ingresa una URL y un nivel",
    body: "Pega cualquier dominio y elige qué tan a fondo escanear: básico pasivo, intermedio o avanzado (con autorización).",
  },
  {
    icon: Radar,
    title: "El equipo de agentes audita",
    body: "Un orquestador (Opus) coordina dos agentes (Sonnet) que corren Nuclei, ZAP, testssl y más, mientras sondean la IA embebida. Todo en vivo, paso a paso.",
  },
  {
    icon: Award,
    title: "Recibe tu grado A–F",
    body: "Un reporte de dos capas: ejecutiva (qué pasa y por qué importa) y técnica (evidencia, impacto y remediación paso a paso).",
  },
];

function SignalConnector({ reduced }: { reduced: boolean }) {
  return (
    <div aria-hidden className="hidden w-14 shrink-0 self-center lg:block">
      <svg viewBox="0 0 56 16" className="h-4 w-full" fill="none">
        <line
          x1="4"
          y1="8"
          x2="52"
          y2="8"
          stroke="var(--outline-variant)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <line
          x1="4"
          y1="8"
          x2="52"
          y2="8"
          stroke="var(--primary)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="6 10"
          className={cn(!reduced && "animate-signal-trace")}
        />
        <circle cx="52" cy="8" r="3.5" fill="var(--primary)" />
      </svg>
    </div>
  );
}

export function LandingSteps() {
  const reduced = useReducedMotion();
  return (
    <div className="relative flex flex-col items-stretch gap-4 lg:flex-row lg:gap-0">
      {STEPS.map((step, i) => {
        const Icon = step.icon;
        return (
          <React.Fragment key={step.title}>
            <div className="group relative flex flex-1 flex-col gap-5 overflow-hidden rounded-[1.75rem] bg-surface-container-low p-6 transition-[background-color,transform] duration-300 ease-emphasized hover:-translate-y-0.5 hover:bg-surface-container">
              <div
                aria-hidden
                className={cn(
                  "absolute inset-x-6 top-0 h-1 rounded-b-full",
                  i === 0 && "bg-primary",
                  i === 1 && "bg-secondary",
                  i === 2 && "bg-tertiary"
                )}
              />
              <div className="flex items-center gap-3.5">
                <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-tertiary-container font-mono text-lg font-bold text-on-tertiary-container shadow-[inset_0_0_0_1px_color-mix(in_oklab,var(--tertiary)_22%,transparent)]">
                  {i + 1}
                </span>
                <span className="grid size-10 place-items-center rounded-full bg-surface-container-lowest text-primary transition-transform duration-300 ease-emphasized group-hover:scale-105">
                  <Icon className="size-5" />
                </span>
              </div>
              <h3 className="text-xl font-bold text-foreground">
                {step.title}
              </h3>
              <p className="text-[15px] leading-relaxed text-on-surface-variant">
                {step.body}
              </p>
            </div>
            {i < STEPS.length - 1 && <SignalConnector reduced={reduced} />}
          </React.Fragment>
        );
      })}
    </div>
  );
}
