import type { TenantStatus } from "@/src/domain/enums/tenants";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { TenantsResponse } from "@/src/domain/responses/tenant";

export interface TenantFilters {
  status?: TenantStatus;
  search?: string;
}

export interface TenantRepository {
  getUserTenants(
    filters?: TenantFilters
  ): Promise<TenantsResponse | ErrorFeeback>;
  setCurrentTenant(
    tenantId: string
  ): Promise<TaskResultResponse | ErrorFeeback>;
}
