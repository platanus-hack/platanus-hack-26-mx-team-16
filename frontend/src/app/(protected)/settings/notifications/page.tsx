"use client";

import { NotificationsView } from "@/src/presentation/owliver/settings/notifications-view";
import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";

export default function NotificationsPage() {
  return (
    <SettingsShell activePath="/settings/notifications">
      <NotificationsView />
    </SettingsShell>
  );
}
