"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * "Conexiones" was merged into "Integraciones" (single org-level integrations
 * registry). Kept as a redirect so existing links and bookmarks don't break.
 */
export default function ConnectionsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/integrations");
  }, [router]);

  return null;
}
