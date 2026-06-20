import { create } from "zustand";

import { useSessionStore } from "@/src/application/contexts/session-store";
import type { Tenant } from "@/src/domain/entities/tenant";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import type { TenantFilters } from "@/src/domain/repositories/tenant";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpTenantRepository } from "@/src/infrastructure/repositories/http-tenant";

const tenantsRepository = new HttpTenantRepository(authHttp);

interface TenantsState {
  tenants: Tenant[];
  loading: boolean;
  error: ErrorFeeback | null;
  fetchTenants: (filters?: TenantFilters) => Promise<void>;
  selectTenant: (tenant: Tenant) => Promise<void>;
  clearError: () => void;
}

export const useTenantStore = create<TenantsState>()((set) => ({
  tenants: [],
  loading: false,
  error: null,

  fetchTenants: async (filters) => {
    set({ loading: true, error: null });
    try {
      const result = await tenantsRepository.getUserTenants(filters);
      if (isErrorFeedback(result)) {
        set({ loading: false, error: result, tenants: [] });
        return;
      }
      set({ loading: false, error: null, tenants: result.data });
    } catch (err) {
      console.error("Error fetching tenants:", err);
      set({ loading: false, error: genericServerError, tenants: [] });
    }
  },

  selectTenant: async (tenant) => {
    const session = useSessionStore.getState();
    const previous = session.tenant;

    session.setTenant(tenant);

    const result = await tenantsRepository.setCurrentTenant(tenant.uuid);
    if (isErrorFeedback(result) && previous) {
      session.setTenant(previous);
    }
  },

  clearError: () => set({ error: null }),
}));

export const useTenants = () => useTenantStore((s) => s.tenants);
export const useTenantsLoading = () => useTenantStore((s) => s.loading);
export const useTenantsError = () => useTenantStore((s) => s.error);
