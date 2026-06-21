"use client";

import { SettingsShell } from "@/src/presentation/owliver/settings/settings-shell";
import { ProfileView } from "@/src/presentation/profile/profile-view";

export default function ProfilePage() {
  return (
    <SettingsShell activePath="/profile">
      <ProfileView />
    </SettingsShell>
  );
}
