"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { SettingsView } from "@/src/presentation/settings/settings-view";

export default function SettingsPage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="tenant_settings.update">
      <AppShell
        activePath="/settings"
        breadcrumbItems={[{ label: t("settings") }]}
      >
        <SettingsView />
      </AppShell>
    </PermissionGuard>
  );
}
