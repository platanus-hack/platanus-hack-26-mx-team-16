"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { MembersView } from "@/src/presentation/members/members-view";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";

export default function MembersPage() {
  return (
    <PermissionGuard permission="tenant_users.view">
      <SettingsShell activePath="/members">
        <MembersView />
      </SettingsShell>
    </PermissionGuard>
  );
}
