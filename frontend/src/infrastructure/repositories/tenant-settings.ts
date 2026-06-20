import type { AxiosError, AxiosInstance } from "axios";

import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { TenantSettings } from "@/src/domain/entities/tenant-settings";
import type { TenantSettingsRepository } from "@/src/domain/repositories/tenant-settings";
import type { TenantSettingsResponse } from "@/src/domain/responses/tenant-settings";
import { useSessionStore } from "@/src/application/contexts/session-store";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpTenantSettingsRepository implements TenantSettingsRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  private get tenantId(): string {
    const id = useSessionStore.getState().tenant?.uuid;
    if (!id) throw new Error("No active tenant");
    return id;
  }

  async get(): Promise<TenantSettingsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: TenantSettings }>(
        `/v1/tenants/${this.tenantId}/settings`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(name: string): Promise<TenantSettingsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.patch<{ data: TenantSettings }>(
        `/v1/tenants/${this.tenantId}/settings`,
        { name }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updateAvatar(
    file: File
  ): Promise<TenantSettingsResponse | ErrorFeeback> {
    try {
      const form = new FormData();
      form.append("avatar", file);
      const response = await this.httpClient.post<{ data: TenantSettings }>(
        `/v1/tenants/${this.tenantId}/settings/avatar`,
        form
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async regenerateWebhookKey(): Promise<TenantSettingsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: TenantSettings }>(
        `/v1/tenants/${this.tenantId}/settings/webhook-key`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async deleteTenant(): Promise<{ success: boolean } | ErrorFeeback> {
    try {
      await this.httpClient.delete(`/v1/tenants/${this.tenantId}`);
      return { success: true };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
