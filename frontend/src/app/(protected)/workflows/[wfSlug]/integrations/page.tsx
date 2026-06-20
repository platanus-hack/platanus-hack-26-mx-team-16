"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * "Integrations" was renamed/restructured into "Connections" (Sources /
 * Destinations). The webhook config that used to live here is now the first
 * destination under Connections › Destinations. Kept as a redirect so existing
 * links and bookmarks don't break.
 */
export default function WorkflowIntegrationsRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;

  useEffect(() => {
    if (wfSlug) {
      router.replace(`/workflows/${wfSlug}/connections/destinations`);
    }
  }, [wfSlug, router]);

  return null;
}
