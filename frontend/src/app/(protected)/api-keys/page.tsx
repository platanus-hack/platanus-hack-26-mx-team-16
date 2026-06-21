"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";
import { ApiKeysView } from "@/src/presentation/settings/api-keys-view";

export default function ApiKeysPage() {
  return (
    <PermissionGuard permission="tenant_settings.update">
      <SettingsShell activePath="/api-keys">
        <ApiKeysView />
      </SettingsShell>
    </PermissionGuard>
  );
}
