"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { UsageView } from "@/src/presentation/usage/usage-view";

export default function UsagePage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="workflows.view_usage">
      <AppShell activePath="/usage" breadcrumbItems={[{ label: t("usage") }]}>
        <UsageView />
      </AppShell>
    </PermissionGuard>
  );
}
