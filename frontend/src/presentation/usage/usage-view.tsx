"use client";

import { useTranslations } from "next-intl";

import { useUsageSummaryQuery } from "@/src/application/hooks/queries/usage";
import { Card, CardContent } from "@/src/presentation/components/ui/card";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import { ProcessRecordsTable } from "./process-records-table";
import { UsageQuotaCard } from "./usage-quota-card";

function SummarySkeletons() {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-5 space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-2 w-full rounded-full" />
        <Skeleton className="h-3 w-72" />
      </CardContent>
    </Card>
  );
}

export function UsageView() {
  const t = useTranslations("Usage");
  const { data: summary, isLoading } = useUsageSummaryQuery();

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-4">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
        <p className="text-muted-foreground mt-1 text-sm">{t("subtitle")}</p>
      </div>

      {isLoading || !summary ? <SummarySkeletons /> : <UsageQuotaCard summary={summary} />}

      <div className="flex flex-col flex-1 min-h-0">
        <ProcessRecordsTable />
      </div>
    </div>
  );
}
