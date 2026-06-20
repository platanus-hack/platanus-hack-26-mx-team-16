import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  DeleteResponse,
  InviteMemberPayload,
  InviteMembersResult,
  PendingInvitation,
  UpdateTenantUserPayload,
  TenantUserRepository,
} from "@/src/domain/repositories/tenant-user";
import type {
  TenantUserListResponse,
  TenantUserResponse,
} from "@/src/domain/responses/tenant-user";
import type { TenantUser } from "@/src/domain/entities/tenants/tenant-user";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpTenantUserRepository implements TenantUserRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(): Promise<TenantUserListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: TenantUser[] }>(
        "/v1/tenants/users"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async invite(
    payload: InviteMemberPayload
  ): Promise<InviteMembersResult | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: InviteMembersResult }>(
        "/v1/tenants/invitations",
        { members: [{ email: payload.email, roleSlug: payload.roleSlug }] }
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listPendingInvitations(): Promise<PendingInvitation[] | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: PendingInvitation[] }>(
        "/v1/tenants/invitations"
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async cancelInvitation(
    invitationId: string
  ): Promise<PendingInvitation | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<{ data: PendingInvitation }>(
        `/v1/tenants/invitations/${encodeURIComponent(invitationId)}`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async sendPasswordReset(
    tenantUserId: string
  ): Promise<{ email: string } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: { email: string } }>(
        `/v1/tenants/users/${encodeURIComponent(tenantUserId)}/send-password-reset`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async uploadPhoto(
    uuid: string,
    file: File
  ): Promise<TenantUserResponse | ErrorFeeback> {
    try {
      const form = new FormData();
      form.append("photo", file);
      const response = await this.httpClient.post<{ data: TenantUser }>(
        `/v1/tenants/users/${encodeURIComponent(uuid)}/photo`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(uuid: string): Promise<TenantUserResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: TenantUser }>(
        `/v1/tenants/users/${uuid}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    uuid: string,
    payload: UpdateTenantUserPayload
  ): Promise<TenantUserResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: TenantUser }>(
        `/v1/tenants/users/${uuid}`,
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
        `/v1/tenants/users/${uuid}`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
