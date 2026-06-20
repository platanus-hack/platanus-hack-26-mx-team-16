"use client";

import { ShieldCheck } from "lucide-react";

interface Props {
  completed: number;
  total: number;
  isCanceling?: boolean;
  /**
   * When true, the parent's bottom pane is occupying vertical space, so we
   * top-align the content (with breathing room) instead of vertically
   * centering it — otherwise the message ends up hugging the pane edge.
   */
  paneOpen?: boolean;
}

export function AnalysisRunningState({
  completed,
  total,
  isCanceling = false,
  paneOpen = false,
}: Props) {
  const hasTotal = total > 0;
  const percent = hasTotal
    ? Math.min(100, Math.round((completed / total) * 100))
    : 0;
  const indeterminate = !hasTotal && !isCanceling;

  return (
    <div
      className={`flex h-full w-full justify-center rounded-lg border border-dashed p-6 ${
        paneOpen ? "items-start pt-12" : "items-center"
      }`}
    >
      <div className="flex w-full max-w-[360px] flex-col items-center gap-4 text-center">
        <div className="relative flex size-14 items-center justify-center">
          <PulseRing delay={0} />
          <PulseRing delay={700} />
          <div className="relative flex size-10 items-center justify-center rounded-full border border-primary/40 bg-card">
            <ShieldCheck
              className={`size-5 text-primary ${
                isCanceling ? "opacity-60" : ""
              }`}
            />
          </div>
        </div>

        <div className="space-y-1">
          <h3 className="text-sm font-semibold tracking-tight">
            {isCanceling ? "Cancelando análisis…" : "Análisis en curso"}
          </h3>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {isCanceling
              ? "Deteniendo la evaluación. Los resultados parciales se conservarán."
              : "Evaluando las reglas activas. Los resultados aparecerán a medida que se completen."}
          </p>
        </div>

        <div className="w-full space-y-1.5">
          <div className="flex items-baseline justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            <span>
              {hasTotal ? (
                <>
                  <span className="tabular-nums text-foreground">
                    {completed.toString().padStart(2, "0")}
                  </span>
                  <span className="mx-1 text-muted-foreground/50">/</span>
                  <span className="tabular-nums">
                    {total.toString().padStart(2, "0")}
                  </span>{" "}
                  reglas
                </>
              ) : (
                "preparando"
              )}
            </span>
            <span className="tabular-nums text-foreground/70">
              {hasTotal ? `${percent}%` : "—"}
            </span>
          </div>
          <div className="relative h-0.5 overflow-hidden rounded-full bg-muted">
            {indeterminate ? (
              <span className="absolute inset-y-0 -left-1/3 w-1/3 animate-[analysis-sweep_1.6s_ease-in-out_infinite] rounded-full bg-primary/70" />
            ) : (
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-500 ease-out"
                style={{ width: `${percent}%` }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PulseRing({ delay }: { delay: number }) {
  return (
    <span
      aria-hidden
      className="absolute inset-0 rounded-full border border-primary/50 opacity-0 animate-[analysis-pulse_1.8s_cubic-bezier(0,0,0.2,1)_infinite]"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}
