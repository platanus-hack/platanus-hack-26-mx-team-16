"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { ProfileView } from "@/src/presentation/profile/profile-view";

export default function ProfilePage() {
  const t = useTranslations("NavUser");
  return (
    <AppShell activePath="/profile" breadcrumbItems={[{ label: t("profile") }]}>
      <ProfileView />
    </AppShell>
  );
}
