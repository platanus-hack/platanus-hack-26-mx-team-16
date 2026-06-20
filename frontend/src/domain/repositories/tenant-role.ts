import type { TenantRoleStatus } from "@/src/domain/enums/tenants";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  TenantRoleListResponse,
  TenantRoleResponse,
} from "@/src/domain/responses/tenant-role";

export interface CreateTenantRolePayload {
  name: string;
  permissions: string[];
  status: TenantRoleStatus;
}

export interface UpdateTenantRolePayload {
  name?: string;
  permissions?: string[];
  status?: TenantRoleStatus;
}

export interface DeleteResponse {
  status: string;
}

export interface TenantRoleRepository {
  getAll(): Promise<TenantRoleListResponse | ErrorFeeback>;
  getById(uuid: string): Promise<TenantRoleResponse | ErrorFeeback>;
  create(
    payload: CreateTenantRolePayload
  ): Promise<TenantRoleResponse | ErrorFeeback>;
  update(
    uuid: string,
    payload: UpdateTenantRolePayload
  ): Promise<TenantRoleResponse | ErrorFeeback>;
  delete(uuid: string): Promise<DeleteResponse | ErrorFeeback>;
}
