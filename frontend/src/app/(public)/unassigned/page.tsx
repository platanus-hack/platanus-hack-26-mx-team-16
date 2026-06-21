import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { refreshServerSession } from "@/src/infrastructure/auth/server-session";
import { UnassignedView } from "@/src/presentation/auth/unassigned-view";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("Unassigned");
  return {
    title: t("metadataTitle"),
    description: t("metadataDescription"),
  };
}

export default async function UnassignedPage() {
  const session = await refreshServerSession();

  // No valid session -> back to login.
  if (!session) {
    redirect("/login");
  }

  // Already has a tenant -> nothing to do here, send home.
  if (session.tenant) {
    redirect("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <UnassignedView />
    </div>
  );
}
