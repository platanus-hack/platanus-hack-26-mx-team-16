"use client";

import { createContext, useContext } from "react";
import { useSessionStore } from "@/src/application/contexts/session-store";
import type { Tenant } from "@/src/domain/entities/tenant";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { User } from "@/src/domain/entities/user";

interface SessionContextType {
  user: User | null;
  tenant: Tenant | null;
  tenantRole: TenantRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const user = useSessionStore((state) => state.user);
  const tenant = useSessionStore((state) => state.tenant);
  const tenantRole = useSessionStore((state) => state.tenantRole);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated());
  const _synced = useSessionStore((state) => state._synced);

  const isLoading = !_synced;

  const value = {
    user,
    tenant,
    tenantRole,
    isAuthenticated,
    isLoading,
  };

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}

// Hook para acceder a las acciones del store
export function useSessionActions() {
  return {
    setSession: useSessionStore((state) => state.setSession),
    setAccessToken: useSessionStore((state) => state.setAccessToken),
    clearSession: useSessionStore((state) => state.clearSession),
  };
}
