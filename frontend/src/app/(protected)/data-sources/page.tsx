"use client";

import { Database } from "lucide-react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { EmptyState } from "@/src/presentation/components/common/empty-state";

export default function DataSourcesPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("DataSources");
  return (
    <AppShell
      activePath="/data-sources"
      breadcrumbItems={[{ label: tNav("dataSources") }]}
    >
      <EmptyState
        icon={Database}
        title={t("emptyTitle")}
        description={t("emptyDescription")}
        actionLabel={t("add")}
        onAction={() => console.log("Add data source")}
      />
    </AppShell>
  );
}
