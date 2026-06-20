import type {
  AssignableUser,
  WorkflowMember,
  WorkflowPermissions,
} from "@/src/domain/entities/workflow-permission";

export interface WorkflowPermissionsResponse {
  data: WorkflowPermissions;
}

export interface WorkflowMemberResponse {
  data: WorkflowMember;
}

export interface AssignableUsersResponse {
  data: AssignableUser[];
}
