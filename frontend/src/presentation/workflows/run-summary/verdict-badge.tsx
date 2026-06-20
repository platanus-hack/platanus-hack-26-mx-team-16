"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import type { Verdict } from "@/src/domain/entities/run-summary";

import { VERDICT_TONE } from "./verdict-config";

interface VerdictBadgeProps {
  verdict: Verdict;
  size?: "sm" | "lg";
  className?: string;
}

export function VerdictBadge({
  verdict,
  size = "sm",
  className,
}: VerdictBadgeProps) {
  const t = useTranslations("RunSummary");
  const tone = VERDICT_TONE[verdict];
  if (size === "lg") {
    return (
      <div
        className={cn(
          "inline-flex items-center justify-center rounded-md border-2 bg-card",
          "px-6 py-4 font-serif text-3xl font-medium tracking-tight tabular-nums",
          tone.border,
          tone.text,
          className
        )}
        aria-label={t("verdictAria", { label: tone.label })}
      >
        {tone.glyph}
      </div>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded border px-1.5 font-mono text-[10px] uppercase tracking-[0.18em]",
        tone.border,
        tone.text,
        className
      )}
      aria-label={t("verdictAria", { label: tone.label })}
    >
      {tone.glyph}
    </span>
  );
}
