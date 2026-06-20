"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * "Conexiones" is a sidebar group with two sub-pages (sources / destinations).
 * Visiting the bare /connections route (e.g. a bookmark) redirects to Sources,
 * the first sub-page.
 */
export default function WorkflowConnectionsRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;

  useEffect(() => {
    if (wfSlug) {
      router.replace(`/workflows/${wfSlug}/connections/sources`);
    }
  }, [wfSlug, router]);

  return null;
}
