"use client";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { ApiKeysView } from "@/src/presentation/settings/api-keys-view";

export default function ApiKeysPage() {
  return (
    <PermissionGuard permission="tenant_settings.update">
      <AppShell activePath="/api-keys" breadcrumbItems={[{ label: "API Keys" }]}>
        <ApiKeysView />
      </AppShell>
    </PermissionGuard>
  );
}
