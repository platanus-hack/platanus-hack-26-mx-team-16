"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { MembersView } from "@/src/presentation/members/members-view";

export default function MembersPage() {
  const t = useTranslations("Nav");
  return (
    <PermissionGuard permission="tenant_users.view">
      <AppShell
        activePath="/members"
        breadcrumbItems={[{ label: t("members") }]}
      >
        <MembersView />
      </AppShell>
    </PermissionGuard>
  );
}
