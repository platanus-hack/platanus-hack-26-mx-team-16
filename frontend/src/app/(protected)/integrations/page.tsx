"use client";

import { useTranslations } from "next-intl";

import { AppShell } from "@/src/presentation/common/app-shell";
import { ConnectionsView } from "@/src/presentation/connections/connections-view";

export default function IntegrationsPage() {
  const t = useTranslations("Nav");
  return (
    <AppShell
      activePath="/integrations"
      breadcrumbItems={[{ label: t("integrations") }]}
    >
      <ConnectionsView />
    </AppShell>
  );
}
