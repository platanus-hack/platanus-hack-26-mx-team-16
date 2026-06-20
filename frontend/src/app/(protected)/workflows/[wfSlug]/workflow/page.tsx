"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * The workflow configuration used to live here as a tabbed page. Each tab is now
 * an independent page under the Settings section of the workflow sidebar
 * (document-types, knowledge, analysis-rules, synthesis, integrations,
 * permissions). This route is kept as a redirect to the first settings page so
 * existing links and bookmarks don't break.
 */
export default function WorkflowConfigRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;

  useEffect(() => {
    if (wfSlug) {
      router.replace(`/workflows/${wfSlug}/document-types`);
    }
  }, [wfSlug, router]);

  return null;
}
