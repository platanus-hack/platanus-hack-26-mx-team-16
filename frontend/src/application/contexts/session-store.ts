import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Tenant } from "@/src/domain/entities/tenant";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { User } from "@/src/domain/entities/user";

interface SessionState {
  // Session data
  user: User | null;
  tenant: Tenant | null;
  tenantRole: TenantRole | null;
  accessToken: string | null;
  _synced: boolean;

  // Actions
  setSession: (
    user: User,
    tenant: Tenant | null,
    tenantRole: TenantRole | null,
    accessToken: string
  ) => void;
  setUser: (user: User) => void;
  setAccessToken: (accessToken: string) => void;
  setTenant: (tenant: Tenant) => void;
  clearTenant: () => void;
  clearSession: () => void;

  // Computed
  isAuthenticated: () => boolean;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      tenant: null,
      tenantRole: null,
      accessToken: null,
      _synced: false,

      // Actions
      setSession: (user, tenant, tenantRole, accessToken) => {
        set({
          user,
          tenant,
          tenantRole,
          accessToken,
          _synced: true,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      setAccessToken: (accessToken) => {
        set({ accessToken });
      },

      setTenant: (tenant) => {
        set({ tenant });
      },

      clearTenant: () => {
        set({ tenant: null, tenantRole: null });
      },

      clearSession: () => {
        set({
          user: null,
          tenant: null,
          tenantRole: null,
          accessToken: null,
          _synced: false,
        });
      },

      // Computed
      isAuthenticated: () => {
        const state = get();
        return (
          state.user !== null &&
          state.tenant !== null &&
          state.accessToken !== null
        );
      },
    }),
    {
      name: "session-storage",
      partialize: (state) => ({
        // Solo persistir datos del usuario, NO tokens
        user: state.user,
        tenant: state.tenant,
        tenantRole: state.tenantRole,
      }),
    }
  )
);
