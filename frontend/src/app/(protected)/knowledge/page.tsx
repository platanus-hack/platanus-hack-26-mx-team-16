import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/src/presentation/common/app-shell";
import { KnowledgeView } from "@/src/presentation/knowledge/knowledge-view";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("Knowledge");
  return { title: t("metadataTitle") };
}

export default async function KnowledgePage() {
  const t = await getTranslations("Nav");
  return (
    <AppShell
      activePath="/knowledge"
      breadcrumbItems={[{ label: t("knowledge") }]}
    >
      <KnowledgeView />
    </AppShell>
  );
}
