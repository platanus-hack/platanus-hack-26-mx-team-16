"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { DashboardView } from "@/src/presentation/dashboard/dashboard-view";

export default function DashboardPage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="dashboard.view">
      <AppShell
        activePath="/dashboard"
        breadcrumbItems={[{ label: t("dashboard") }]}
      >
        <DashboardView />
      </AppShell>
    </PermissionGuard>
  );
}
