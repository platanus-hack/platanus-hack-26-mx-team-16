"use client";

import {
  AlertTriangle,
  BookOpen,
  CalendarDays,
  CheckCircle,
  FileText,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";

import type { UsageSummary } from "@/src/domain/entities/usage";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Card, CardContent } from "@/src/presentation/components/ui/card";

interface UsageQuotaCardProps {
  summary: UsageSummary;
}

export function UsageQuotaCard({ summary }: UsageQuotaCardProps) {
  const t = useTranslations("UsageQuotaCard");
  const tUsage = useTranslations("Usage");
  const pct = summary.usagePct ?? 0;

  const excessPages =
    summary.monthlyQuota !== null
      ? Math.max(0, summary.pagesUsed - summary.monthlyQuota)
      : 0;
  const isOver = excessPages > 0;

  const total = Math.max(
    summary.pagesUsed,
    summary.monthlyQuota ?? summary.pagesUsed,
    1,
  );
  const greenPct =
    summary.monthlyQuota !== null
      ? (Math.min(summary.pagesUsed, summary.monthlyQuota) / total) * 100
      : 0;
  const redPct = (excessPages / total) * 100;

  const quotaLabel =
    summary.monthlyQuota === null
      ? t("unlimited")
      : summary.monthlyQuota.toLocaleString();

  const planLabel =
    summary.monthlyQuota === null
      ? tUsage("plan.enterprise")
      : summary.monthlyQuota >= 25_000
        ? tUsage("plan.business")
        : summary.monthlyQuota >= 5_000
          ? tUsage("plan.pro")
          : tUsage("plan.starter");

  const statusBadge = summary.isAtLimit ? (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="h-3 w-3" />
      {t("limitReached")}
    </Badge>
  ) : summary.isNearLimit ? (
    <Badge
      variant="outline"
      className="gap-1 border-yellow-500 text-yellow-600"
    >
      <AlertTriangle className="h-3 w-3" />
      {t("highUsage")}
    </Badge>
  ) : (
    <Badge
      variant="outline"
      className="gap-1 border-emerald-500 text-emerald-600"
    >
      <CheckCircle className="h-3 w-3" />
      {t("normal")}
    </Badge>
  );

  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-5 space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">{t("title")}</span>
          </div>
          {statusBadge}
        </div>

        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-foreground">
              {t("pagesUsed", { count: summary.pagesUsed.toLocaleString() })}
            </span>
            <span className="text-muted-foreground">
              {summary.monthlyQuota === null
                ? t("unlimitedLabel")
                : t("ofQuota", { value: quotaLabel })}
              {summary.monthlyQuota !== null && (
                <span className="ml-2 text-muted-foreground/70">
                  {pct.toFixed(1)}%
                </span>
              )}
            </span>
          </div>
          <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
            {summary.monthlyQuota !== null && (
              <>
                <div
                  className="h-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${greenPct}%` }}
                />
                {isOver && (
                  <div
                    className="h-full bg-destructive transition-all duration-500"
                    style={{ width: `${redPct}%` }}
                  />
                )}
              </>
            )}
          </div>
        </div>

        {/* Compact stats row */}
        <div className="flex items-center gap-4 border-t pt-2.5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5 shrink-0" />
            <span>
              {t("periodPrefix")}{" "}
              <span className="font-medium text-foreground">
                {t("periodRange", {
                  from: summary.periodStart,
                  to: summary.periodEnd,
                })}
              </span>
            </span>
          </span>
          <span className="text-border">·</span>
          <span className="flex items-center gap-1.5">
            <CalendarDays className="h-3.5 w-3.5 shrink-0" />
            <span className="font-medium text-foreground">
              {t("daysRemaining", { count: summary.daysRemaining })}
            </span>
          </span>
          <span className="text-border">·</span>
          <span className="flex items-center gap-1.5">
            <BookOpen className="h-3.5 w-3.5 shrink-0" />
            <span className="font-medium text-foreground">{planLabel}</span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
