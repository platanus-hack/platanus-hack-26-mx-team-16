import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { UnassignedView } from "@/src/presentation/auth/unassigned-view";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("Unassigned");
  return {
    title: t("metadataTitle"),
    description: t("metadataDescription"),
  };
}

export default function UnassignedPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <UnassignedView />
    </div>
  );
}
