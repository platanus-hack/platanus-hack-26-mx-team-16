import type {
  WorkflowAccessType,
  WorkflowMemberRole,
} from "@/src/domain/entities/workflow-permission";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { DeleteResponse } from "@/src/domain/repositories/workflow";
import type {
  AssignableUsersResponse,
  WorkflowMemberResponse,
  WorkflowPermissionsResponse,
} from "@/src/domain/responses/workflow-permission";

export interface WorkflowPermissionRepository {
  getPermissions(
    workflowUuid: string
  ): Promise<WorkflowPermissionsResponse | ErrorFeeback>;

  listAssignableUsers(
    workflowUuid: string
  ): Promise<AssignableUsersResponse | ErrorFeeback>;

  updateAccessType(
    workflowUuid: string,
    accessType: WorkflowAccessType
  ): Promise<WorkflowPermissionsResponse | ErrorFeeback>;

  addMember(
    workflowUuid: string,
    userId: string,
    role: WorkflowMemberRole
  ): Promise<WorkflowMemberResponse | ErrorFeeback>;

  updateMemberRole(
    workflowUuid: string,
    userId: string,
    role: WorkflowMemberRole
  ): Promise<WorkflowMemberResponse | ErrorFeeback>;

  removeMember(
    workflowUuid: string,
    userId: string
  ): Promise<DeleteResponse | ErrorFeeback>;
}
