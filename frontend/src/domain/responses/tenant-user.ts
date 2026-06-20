import type { TenantUser } from "@/src/domain/entities/tenants/tenant-user";

export interface TenantUserResponse {
  data: TenantUser;
}

export interface TenantUserListResponse {
  data: TenantUser[];
}
