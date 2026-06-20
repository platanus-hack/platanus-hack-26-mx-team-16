export type WorkflowAccessType = "organization" | "private";

export type WorkflowMemberRole = "admin" | "member" | "viewer";

export interface WorkflowMember {
  uuid: string;
  userId: string;
  name: string;
  email: string | null;
  role: WorkflowMemberRole;
  photo?: string | null;
  isOwner?: boolean;
}

export interface WorkflowPermissions {
  workflowId: string;
  accessType: WorkflowAccessType;
  members: WorkflowMember[];
}

/** A tenant member not yet on the workflow — shown in the add-member picker. */
export interface AssignableUser {
  userId: string;
  tenantUserId: string;
  name: string;
  email: string | null;
  photo?: string | null;
  isOwner?: boolean;
}
