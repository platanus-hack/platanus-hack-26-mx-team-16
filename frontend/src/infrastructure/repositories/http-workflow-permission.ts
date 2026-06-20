import type { AxiosError, AxiosInstance } from "axios";
import type {
  AssignableUser,
  WorkflowAccessType,
  WorkflowMember,
  WorkflowMemberRole,
  WorkflowPermissions,
} from "@/src/domain/entities/workflow-permission";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { DeleteResponse } from "@/src/domain/repositories/workflow";
import type { WorkflowPermissionRepository } from "@/src/domain/repositories/workflow-permission";
import type {
  AssignableUsersResponse,
  WorkflowMemberResponse,
  WorkflowPermissionsResponse,
} from "@/src/domain/responses/workflow-permission";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpWorkflowPermissionRepository
  implements WorkflowPermissionRepository
{
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getPermissions(
    workflowUuid: string
  ): Promise<WorkflowPermissionsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowPermissions }>(
        `/v1/workflows/${workflowUuid}/permissions`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listAssignableUsers(
    workflowUuid: string
  ): Promise<AssignableUsersResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: AssignableUser[] }>(
        `/v1/workflows/${workflowUuid}/permissions/assignable-users`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updateAccessType(
    workflowUuid: string,
    accessType: WorkflowAccessType
  ): Promise<WorkflowPermissionsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: WorkflowPermissions }>(
        `/v1/workflows/${workflowUuid}/permissions/access-type`,
        { accessType }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async addMember(
    workflowUuid: string,
    userId: string,
    role: WorkflowMemberRole
  ): Promise<WorkflowMemberResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowMember }>(
        `/v1/workflows/${workflowUuid}/permissions/members`,
        { userId, role }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updateMemberRole(
    workflowUuid: string,
    userId: string,
    role: WorkflowMemberRole
  ): Promise<WorkflowMemberResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.patch<{ data: WorkflowMember }>(
        `/v1/workflows/${workflowUuid}/permissions/members/${userId}`,
        { role }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async removeMember(
    workflowUuid: string,
    userId: string
  ): Promise<DeleteResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<{ data: DeleteResponse }>(
        `/v1/workflows/${workflowUuid}/permissions/members/${userId}`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
