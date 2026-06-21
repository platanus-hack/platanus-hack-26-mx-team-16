"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";
import { SettingsView } from "@/src/presentation/settings/settings-view";

export default function SettingsPage() {
  return (
    <PermissionGuard permission="tenant_settings.update">
      <SettingsShell activePath="/settings">
        <SettingsView />
      </SettingsShell>
    </PermissionGuard>
  );
}
