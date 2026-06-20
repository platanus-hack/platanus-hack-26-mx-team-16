"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import type { SummarySignal } from "@/src/domain/entities/run-summary";
import { ShortId } from "@/src/presentation/components/common/short-id";

interface BlockingFailuresListProps {
  signals: SummarySignal[];
  ruleNamesById?: Record<string, string>;
  className?: string;
}

function readReason(
  detail: Record<string, unknown> | undefined
): string | null {
  if (!detail) return null;
  const reason = detail.reason;
  if (typeof reason === "string" && reason.trim()) return reason;
  return null;
}

export function BlockingFailuresList({
  signals,
  ruleNamesById,
  className,
}: BlockingFailuresListProps) {
  const t = useTranslations("RunSummary");
  const blocking = signals.filter(
    (s) => s.polarity === "FAIL" && s.severity === "BLOCKER"
  );
  if (blocking.length === 0) return null;

  return (
    <section className={cn("space-y-2", className)}>
      <header className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
        {t("blockingFailures")}
      </header>
      <ul className="space-y-3">
        {blocking.map((signal, index) => {
          const reason = readReason(signal.detail);
          const ruleName = ruleNamesById?.[signal.ruleId];
          return (
            <li
              key={`${signal.ruleId}:${signal.kind}:${index}`}
              className="border-l-2 border-rose-500/40 pl-3"
            >
              <div className="flex items-center gap-2">
                <ShortId value={signal.ruleId} />
                {ruleName ? (
                  <p className="truncate text-sm font-medium text-foreground">
                    {ruleName}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground/80">
                    {t("blockingRule")}
                  </p>
                )}
              </div>
              {reason ? (
                <p className="mt-0.5 text-sm text-muted-foreground/90">
                  {reason}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
