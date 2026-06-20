import type { Tenant } from "@/src/domain/entities/tenant";

export interface TenantsResponse {
  data: Tenant[];
}

export interface TenantResponse {
  data: Tenant;
}
