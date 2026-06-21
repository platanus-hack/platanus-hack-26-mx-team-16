"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { DashboardView } from "@/src/presentation/dashboard/dashboard-view";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";

export default function DashboardPage() {
  return (
    <PermissionGuard permission="dashboard.view">
      <SettingsShell activePath="/dashboard">
        <DashboardView />
      </SettingsShell>
    </PermissionGuard>
  );
}
