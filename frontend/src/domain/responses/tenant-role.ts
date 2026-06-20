import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";

export interface TenantRoleResponse {
  data: TenantRole;
}

export interface TenantRoleListResponse {
  data: TenantRole[];
}
