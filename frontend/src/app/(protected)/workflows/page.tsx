"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { WorkflowsView } from "@/src/presentation/workflows/workflows-view";

export default function WorkflowsPage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="workflows.view">
      <AppShell
        activePath="/workflows"
        breadcrumbItems={[{ label: t("workflows") }]}
      >
        <WorkflowsView />
      </AppShell>
    </PermissionGuard>
  );
}
