"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";
import { RolesView } from "@/src/presentation/roles/roles-view";

export default function RolesPage() {
  return (
    <PermissionGuard permission="tenant_roles.view">
      <SettingsShell activePath="/roles">
        <RolesView />
      </SettingsShell>
    </PermissionGuard>
  );
}
