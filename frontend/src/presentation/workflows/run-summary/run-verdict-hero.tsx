"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import type { RunSummary, Verdict } from "@/src/domain/entities/run-summary";
import { ShortId } from "@/src/presentation/components/common/short-id";

import {
  POLARITY_TONE,
  SEVERITY_TONE,
  VERDICT_TONE,
  type Polarity,
  type Severity,
} from "./verdict-config";

interface RunVerdictHeroProps {
  summary: RunSummary;
  className?: string;
}

const POLARITY_ORDER: Polarity[] = ["PASS", "FAIL", "NEUTRAL"];
const SEVERITY_ORDER: Severity[] = ["BLOCKER", "MAJOR", "MINOR", "INFO"];

const TONE_DOT: Record<Verdict, string> = {
  PASS: "bg-emerald-600 dark:bg-emerald-400",
  FAIL: "bg-rose-600 dark:bg-rose-400",
  REVIEW: "bg-amber-500 dark:bg-amber-400",
};

const TONE_TEXT: Record<Verdict, string> = {
  PASS: "text-emerald-700 dark:text-emerald-400",
  FAIL: "text-rose-700 dark:text-rose-400",
  REVIEW: "text-amber-700 dark:text-amber-400",
};

export function RunVerdictHero({ summary, className }: RunVerdictHeroProps) {
  const t = useTranslations("RunSummary");
  const tone = VERDICT_TONE[summary.verdict];
  const evaluated = summary.signals.length;
  const totalRules = evaluated + summary.degradedRules.length;
  const confidence =
    summary.confidenceScore !== null
      ? Math.round(summary.confidenceScore * 100)
      : null;
  const blockers =
    summary.signals.filter(
      (s) => s.polarity === "FAIL" && s.severity === "BLOCKER"
    ).length;
  const polarityTotal = POLARITY_ORDER.reduce(
    (acc, k) => acc + (summary.signalsByPolarity[k] ?? 0),
    0
  );
  const activeSeverity = SEVERITY_ORDER.filter(
    (k) => (summary.signalsBySeverity[k] ?? 0) > 0
  );

  return (
    <header
      className={cn("px-4 py-3", className)}
      aria-label={t("runVerdictAria", { label: tone.label })}
    >
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
        {/* Verdict — dot + word */}
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={cn("h-2 w-2 rounded-full", TONE_DOT[summary.verdict])}
          />
          <span
            className={cn(
              "font-medium tracking-tight",
              TONE_TEXT[summary.verdict]
            )}
          >
            {tone.label}
          </span>
        </div>

        <Sep />

        {confidence !== null ? (
          <>
            <Stat label={t("confidence")} value={`${confidence}%`} />
            <Sep />
          </>
        ) : null}

        <Stat
          label={t("rules")}
          value={`${evaluated}/${totalRules || evaluated}`}
        />

        {polarityTotal > 0 ? (
          <>
            <Sep />
            <ul className="flex items-center gap-3">
              {POLARITY_ORDER.map((key) => {
                const v = summary.signalsByPolarity[key] ?? 0;
                if (v === 0) return null;
                return (
                  <li
                    key={key}
                    className="flex items-center gap-1.5"
                    title={POLARITY_TONE[key].label}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        POLARITY_TONE[key].dot
                      )}
                    />
                    <span className="tabular-nums text-foreground/80">{v}</span>
                  </li>
                );
              })}
            </ul>
          </>
        ) : null}

        {blockers > 0 ? (
          <>
            <Sep />
            <span className="text-xs font-medium text-rose-600 dark:text-rose-400">
              {blockers === 1
                ? t("blockerOne", { count: blockers })
                : t("blockerOther", { count: blockers })}
            </span>
          </>
        ) : null}

        <span className="ml-auto flex items-center gap-3">
          {activeSeverity.length > 0 ? (
            <ul className="flex items-center gap-2.5">
              {activeSeverity.map((key) => {
                const v = summary.signalsBySeverity[key] ?? 0;
                return (
                  <li
                    key={key}
                    className="flex items-center gap-1"
                    title={`${SEVERITY_TONE[key].label}: ${v}`}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        SEVERITY_TONE[key].dot
                      )}
                    />
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
                      {SEVERITY_TONE[key].label.slice(0, 3)}
                    </span>
                    <span className="tabular-nums text-xs text-foreground/80">
                      {v}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : null}
          <ShortId value={summary.workflowAnalysisRunId} />
        </span>
      </div>
    </header>
  );
}

function Sep() {
  return (
    <span aria-hidden className="h-3 w-px bg-border/70" />
  );
}

interface StatProps {
  label: string;
  value: string;
}

function Stat({ label, value }: StatProps) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-xs text-muted-foreground/70">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
