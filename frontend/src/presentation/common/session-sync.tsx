"use client";

import { useEffect } from "react";
import { useSessionActions } from "@/src/application/contexts/session";
import type { TenantUserContext } from "@/src/domain/entities/auth/tenant-user-session";

interface SessionSyncProps {
  session: TenantUserContext;
  /**
   * Fresh access token from the server-side refresh. Without it, sibling
   * components fire their first requests against an empty token in the
   * store and get 401/403'd until the response interceptor refreshes again.
   */
  accessToken: string;
}

export function SessionSync({ session, accessToken }: SessionSyncProps) {
  const { setSession } = useSessionActions();

  // SessionSync is rendered as the first sibling under the Fragment in
  // ProtectedLayout. React fires effects of earlier siblings before those
  // of later siblings, so this effect lands the token in the store before
  // any data-fetching effect inside {children} runs.
  useEffect(() => {
    setSession(session.user, session.tenant, session.tenantRole, accessToken);
  }, [session, accessToken, setSession]);

  return null;
}
