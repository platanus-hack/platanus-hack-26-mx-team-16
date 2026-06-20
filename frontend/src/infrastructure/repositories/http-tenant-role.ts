import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CreateTenantRolePayload,
  DeleteResponse,
  UpdateTenantRolePayload,
  TenantRoleRepository,
} from "@/src/domain/repositories/tenant-role";
import type {
  TenantRoleListResponse,
  TenantRoleResponse,
} from "@/src/domain/responses/tenant-role";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpTenantRoleRepository implements TenantRoleRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(): Promise<TenantRoleListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: TenantRole[] }>(
        "/v1/tenants/roles"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(uuid: string): Promise<TenantRoleResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: TenantRole }>(
        `/v1/tenants/roles/${uuid}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    payload: CreateTenantRolePayload
  ): Promise<TenantRoleResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: TenantRole }>(
        "/v1/tenants/roles",
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    uuid: string,
    payload: UpdateTenantRolePayload
  ): Promise<TenantRoleResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: TenantRole }>(
        `/v1/tenants/roles/${uuid}`,
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(uuid: string): Promise<DeleteResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<{ data: DeleteResponse }>(
        `/v1/tenants/roles/${uuid}`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
