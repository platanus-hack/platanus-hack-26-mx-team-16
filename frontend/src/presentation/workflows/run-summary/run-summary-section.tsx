"use client";

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useRunSummary } from "@/src/application/hooks/use-run-summary";
import { cn } from "@/src/application/lib/utils";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/src/presentation/components/ui/alert";
import { Button } from "@/src/presentation/components/ui/button";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";

import { BlockingFailuresList } from "./blocking-failures-list";
import type { CitationLike } from "./citation-chip";
import { NarrativeRenderer } from "./narrative-renderer";
import { RunVerdictHero } from "./run-verdict-hero";

interface RunSummarySectionProps {
  runId: string | null;
  ruleNamesById?: Record<string, string>;
  onCitationNavigate?: (c: CitationLike) => void;
  className?: string;
}

export function RunSummarySection({
  runId,
  ruleNamesById,
  onCitationNavigate,
  className,
}: RunSummarySectionProps) {
  const t = useTranslations("RunSummary");
  const { summary, isLoading, isResynthesizing, error, resynthesize, reload } =
    useRunSummary({ runId, enableSse: true });
  const [confirmForce, setConfirmForce] = useState(false);

  if (!runId) return null;

  if (isLoading && !summary) {
    return (
      <section
        className={cn(
          "rounded-xl border bg-card p-6 ring-1 ring-foreground/10",
          className
        )}
      >
        <div className="flex items-center gap-6">
          <Skeleton className="h-20 w-32" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-64" />
          </div>
        </div>
      </section>
    );
  }

  if (error && !summary) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="size-4" />
        <AlertTitle>{t("loadErrorTitle")}</AlertTitle>
        <AlertDescription className="flex items-center justify-between gap-3">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={() => reload()}>
            {t("retry")}
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!summary) return null;

  const handleResynthesize = async () => {
    if (summary.narrativeStatus === "COMPLETED" && !confirmForce) {
      setConfirmForce(true);
      return;
    }
    setConfirmForce(false);
    await resynthesize(summary.narrativeStatus === "COMPLETED");
  };

  return (
    <section
      className={cn(
        "overflow-hidden rounded-xl border bg-card ring-1 ring-foreground/10",
        className
      )}
      aria-label={t("ariaLabel")}
    >
      <RunVerdictHero summary={summary} />
      {summary.signals.some(
        (s) => s.polarity === "FAIL" && s.severity === "BLOCKER"
      ) ? (
        <div className="border-t border-border/60 px-8 pt-5 pb-6">
          <BlockingFailuresList
            signals={summary.signals}
            ruleNamesById={ruleNamesById}
          />
        </div>
      ) : null}

      {summary.narrativeStatus !== "SKIPPED" ? (
        <div
          className={cn(
            "border-t bg-gradient-to-b from-muted/30 to-transparent",
            "px-6 pt-5 pb-6"
          )}
        >
          <header className="mb-4 flex items-baseline justify-between gap-4">
            <div className="flex items-baseline gap-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground/70">
                {t("narrative")}
              </p>
              <span className="font-mono text-[10px] text-muted-foreground/60">
                {summary.model ?? "—"} · {summary.provider ?? "—"} · #
                {summary.inputHash.slice(0, 8)}
              </span>
            </div>
            {summary.narrativeStatus === "COMPLETED" ||
            summary.narrativeStatus === "FAILED" ? (
              <Button
                size="sm"
                variant="ghost"
                disabled={isResynthesizing}
                onClick={handleResynthesize}
                aria-label={t("resynthAria")}
              >
                {isResynthesizing ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <RefreshCw className="size-3" />
                )}
                {confirmForce ? t("confirmRerun") : t("resynthesize")}
              </Button>
            ) : null}
          </header>

          <NarrativeBody
            summary={summary}
            onCitationNavigate={onCitationNavigate}
          />
        </div>
      ) : null}
    </section>
  );
}

function NarrativeBody({
  summary,
  onCitationNavigate,
}: {
  summary: NonNullable<ReturnType<typeof useRunSummary>["summary"]>;
  onCitationNavigate?: (c: CitationLike) => void;
}) {
  const t = useTranslations("RunSummary");
  if (summary.narrativeStatus === "RUNNING") {
    return (
      <div className="flex items-center gap-3 py-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        <span>
          {t("synthesizing", { model: summary.model ?? t("defaultModel") })}
        </span>
      </div>
    );
  }
  if (summary.narrativeStatus === "PENDING") {
    return (
      <p className="py-1 text-sm text-muted-foreground/80">
        {t("narrativePending")}
      </p>
    );
  }
  if (summary.narrativeStatus === "FAILED") {
    return (
      <Alert variant="destructive">
        <AlertCircle className="size-4" />
        <AlertTitle>{t("synthesisFailed")}</AlertTitle>
        <AlertDescription>
          {summary.narrativeError ?? t("noErrorDetail")}
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <NarrativeRenderer
      output={summary.output}
      schema={summary.outputSchemaSnapshot}
      onCitationNavigate={onCitationNavigate}
    />
  );
}
