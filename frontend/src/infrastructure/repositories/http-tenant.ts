import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { Tenant } from "@/src/domain/entities/tenant";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  TenantFilters,
  TenantRepository,
} from "@/src/domain/repositories/tenant";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { TenantsResponse } from "@/src/domain/responses/tenant";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpTenantRepository implements TenantRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getUserTenants(
    filters?: TenantFilters
  ): Promise<TenantsResponse | ErrorFeeback> {
    try {
      const params = new URLSearchParams();
      if (filters?.status) params.append("status", filters.status);
      if (filters?.search) params.append("search", filters.search);
      const qs = params.toString();
      const endpoint = `/v1/me/tenants${qs ? `?${qs}` : ""}`;

      const response = await this.httpClient.get<{ data: Tenant[] }>(endpoint);
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async setCurrentTenant(
    tenantId: string
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<TaskResultResponse>(
        `/v1/me/tenants/${tenantId}`
      );
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
