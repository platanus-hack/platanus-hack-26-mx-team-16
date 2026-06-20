"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";

import { POLARITY_TONE, type Polarity } from "./verdict-config";

interface PolarityBarProps {
  counts: Record<string, number>;
  className?: string;
}

const ORDER: Polarity[] = ["PASS", "FAIL", "NEUTRAL"];

export function PolarityBar({ counts, className }: PolarityBarProps) {
  const t = useTranslations("PolarityBar");
  const total = ORDER.reduce((acc, key) => acc + (counts[key] ?? 0), 0);

  return (
    <div className={cn("flex flex-col gap-2", className)} role="group">
      <div
        className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={t("aria")}
      >
        {total > 0
          ? ORDER.map((key) => {
              const value = counts[key] ?? 0;
              if (value === 0) return null;
              const pct = (value / total) * 100;
              return (
                <span
                  key={key}
                  className={cn("h-full transition-all", POLARITY_TONE[key].bar)}
                  style={{ width: `${pct}%` }}
                  title={`${POLARITY_TONE[key].label} · ${value}`}
                />
              );
            })
          : null}
      </div>
      <ul className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs">
        {ORDER.map((key) => {
          const value = counts[key] ?? 0;
          return (
            <li key={key} className="flex items-center gap-2">
              <span
                aria-hidden
                className={cn("h-2 w-2 shrink-0 rounded-full", POLARITY_TONE[key].dot)}
              />
              <span className="font-mono uppercase tracking-[0.15em] text-muted-foreground/80">
                {POLARITY_TONE[key].label}
              </span>
              <span className="font-medium tabular-nums">{value}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
