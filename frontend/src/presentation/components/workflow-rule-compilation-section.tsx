"use client";

import { AlertTriangle, ChevronDown, Loader2 } from "lucide-react";
import { Fragment, memo, useMemo } from "react";
import { cn } from "@/src/application/lib/utils";
import type {
  WorkflowRuleCompilation,
  WorkflowRuleCompilationStatus,
} from "@/src/domain/entities/workflow-rule-compilation";

interface WorkflowRuleCompilationSectionProps {
  compilation: WorkflowRuleCompilation | null;
  isCompiling: boolean;
}

interface StatusVisual {
  word: string;
  badgeTone: string;
}

const STATUS_VISUALS: Record<WorkflowRuleCompilationStatus, StatusVisual> = {
  READY: {
    word: "Compilada",
    badgeTone:
      "bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300",
  },
  COMPILING: {
    word: "Compilando",
    badgeTone:
      "bg-blue-500/10 text-blue-700 ring-blue-500/20 dark:text-blue-300",
  },
  PENDING: {
    word: "En cola",
    badgeTone:
      "bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300",
  },
  FAILED: {
    word: "FALLIDO",
    badgeTone: "bg-red-500/10 text-red-700 ring-red-500/20 dark:text-red-300",
  },
  STALE: {
    word: "Desactualizada",
    badgeTone:
      "bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-300",
  },
};

export const WorkflowRuleCompilationSection = memo(
  function WorkflowRuleCompilationSection({
    compilation,
    isCompiling,
  }: WorkflowRuleCompilationSectionProps) {
    const isEmpty = !compilation && !isCompiling;
    const effectiveStatus: WorkflowRuleCompilationStatus = isCompiling
      ? "COMPILING"
      : (compilation?.status ?? "PENDING");
    const visual = STATUS_VISUALS[effectiveStatus];

    const hasArtifact = Boolean(compilation?.artifact);
    const hasCompiledWith = Boolean(compilation?.compiledWith);
    const showFailedBanner = effectiveStatus === "FAILED" && Boolean(compilation?.error);
    const showStaleBanner = effectiveStatus === "STALE";
    const isExpandable = showFailedBanner || showStaleBanner || hasArtifact || hasCompiledWith;
    // Surface errors/warnings open by default so the user sees them without an extra click.
    const defaultOpen = showFailedBanner || showStaleBanner;

    const compiledWithEntries = useMemo(
      () => Object.entries(compilation?.compiledWith ?? {}),
      [compilation],
    );

    const headerStatus = isEmpty ? (
      <EmptyHeaderStatus />
    ) : (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wider ring-1 ring-inset",
            visual.badgeTone,
          )}
        >
          {effectiveStatus === "COMPILING" ? (
            <Loader2 aria-hidden className="h-3 w-3 animate-spin" />
          ) : null}
          {visual.word}
        </span>
        {compilation?.version ? (
          <span className="inline-flex items-center rounded-md bg-foreground/[0.04] px-2 py-1 font-mono text-[11px] text-muted-foreground ring-1 ring-inset ring-border/60">
            v{compilation.version}
          </span>
        ) : null}
      </div>
    );

    if (!isExpandable) {
      return (
        <section className="flex shrink-0 flex-col overflow-hidden rounded-lg border">
          <header className="flex items-center justify-between gap-3 bg-muted/30 px-3 py-2">
            <h4 className="text-sm font-semibold">Compilación</h4>
            {headerStatus}
          </header>
        </section>
      );
    }

    return (
      <details
        className="group flex shrink-0 flex-col overflow-hidden rounded-lg border [&[open]>summary]:border-b"
        open={defaultOpen || undefined}
      >
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 bg-muted/30 px-3 py-2 hover:bg-muted/50 [&::-webkit-details-marker]:hidden">
          <h4 className="text-sm font-semibold">Compilación</h4>
          <div className="flex items-center gap-2">
            {headerStatus}
            <ChevronDown
              aria-hidden
              className="size-4 text-muted-foreground transition-transform group-open:rotate-180"
            />
          </div>
        </summary>

        <div className="flex flex-col gap-3 p-3">
          {showFailedBanner ? (
            <div className="rounded-md border-l-2 border-red-500/60 bg-red-500/[0.05] px-3 py-2 font-mono text-xs text-red-700 dark:text-red-300">
              {compilation?.error}
            </div>
          ) : null}

          {showStaleBanner ? (
            <div className="flex items-start gap-2 rounded-md border-l-2 border-amber-500/60 bg-amber-500/[0.05] px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Hubo cambios en la regla. La interpretación actual ya no la
                refleja. Reinterpreta para refrescar.
              </span>
            </div>
          ) : null}

          {hasCompiledWith && compiledWithEntries.length > 0 ? (
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-xs">
              {compiledWithEntries.map(([key, value]) => (
                <Fragment key={key}>
                  <dt className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
                    {key}
                  </dt>
                  <dd className="font-mono text-foreground/80">{String(value)}</dd>
                </Fragment>
              ))}
            </dl>
          ) : null}

          {hasArtifact ? (
            <pre className="max-h-48 overflow-auto rounded-md bg-muted/40 p-3 font-mono text-[11px] leading-relaxed">
              {JSON.stringify(compilation?.artifact, null, 2)}
            </pre>
          ) : null}
        </div>
      </details>
    );
  },
);

function EmptyHeaderStatus() {
  return (
    <span className="inline-flex items-center rounded-md bg-muted/60 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground ring-1 ring-inset ring-border/60">
      Sin interpretar
    </span>
  );
}
