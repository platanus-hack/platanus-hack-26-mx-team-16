import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type {
  MemberResponse,
  MemberListResponse,
  MemberInvitationResponse,
  MembersWithInvitationsResponse,
} from "@/src/domain/responses/member";
import type { MemberRole } from "@/src/domain/enums/member-role";

export interface MemberRepository {
  getAll(): Promise<MembersWithInvitationsResponse | ErrorFeeback>;

  getMembers(): Promise<MemberListResponse | ErrorFeeback>;

  getMemberById(uuid: string): Promise<MemberResponse | ErrorFeeback>;

  inviteMember(
    email: string,
    role: MemberRole
  ): Promise<MemberInvitationResponse | ErrorFeeback>;

  updateMemberRole(
    uuid: string,
    role: MemberRole
  ): Promise<MemberResponse | ErrorFeeback>;

  removeMember(uuid: string): Promise<TaskResultResponse | ErrorFeeback>;

  cancelInvitation(uuid: string): Promise<TaskResultResponse | ErrorFeeback>;
}
