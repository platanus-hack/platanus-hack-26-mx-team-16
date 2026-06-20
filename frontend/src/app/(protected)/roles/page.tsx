"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { RolesView } from "@/src/presentation/roles/roles-view";

export default function RolesPage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="tenant_roles.view">
      <AppShell activePath="/roles" breadcrumbItems={[{ label: t("roles") }]}>
        <RolesView />
      </AppShell>
    </PermissionGuard>
  );
}
