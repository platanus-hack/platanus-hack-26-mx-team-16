"use client";

import { useTranslations } from "next-intl";
import { BillingView } from "@/src/presentation/billing/billing-view";
import { AppShell } from "@/src/presentation/common/app-shell";

export default function BillingPage() {
  const t = useTranslations("Nav");
  return (
    <AppShell activePath="/billing" breadcrumbItems={[{ label: t("billing") }]}>
      <BillingView />
    </AppShell>
  );
}
