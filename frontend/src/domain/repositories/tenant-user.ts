import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  TenantUserListResponse,
  TenantUserResponse,
} from "@/src/domain/responses/tenant-user";

export interface InviteMemberPayload {
  email: string;
  roleSlug: string;
}

export interface PendingInvitation {
  uuid: string;
  email: string;
  tenantRoleId: string | null;
  token: string;
  status: string;
  expiresAt: string | null;
  requiresPassword: boolean;
  createdAt: string | null;
}

export interface InviteMembersResult {
  invitations: PendingInvitation[];
  skippedExistingMembers: Array<{ email: string }>;
}

export interface UpdateTenantUserPayload {
  firstName?: string;
  lastName?: string;
  status?: string;
  tenantRoleId?: string;
  isOwner?: boolean;
  isSupport?: boolean;
  email?: string;
}

export interface DeleteResponse {
  status: string;
}

export interface TenantUserRepository {
  getAll(): Promise<TenantUserListResponse | ErrorFeeback>;
  getById(uuid: string): Promise<TenantUserResponse | ErrorFeeback>;
  invite(
    payload: InviteMemberPayload
  ): Promise<InviteMembersResult | ErrorFeeback>;
  listPendingInvitations(): Promise<PendingInvitation[] | ErrorFeeback>;
  cancelInvitation(
    invitationId: string
  ): Promise<PendingInvitation | ErrorFeeback>;
  update(
    uuid: string,
    payload: UpdateTenantUserPayload
  ): Promise<TenantUserResponse | ErrorFeeback>;
  uploadPhoto(
    uuid: string,
    file: File
  ): Promise<TenantUserResponse | ErrorFeeback>;
  delete(uuid: string): Promise<DeleteResponse | ErrorFeeback>;
}
