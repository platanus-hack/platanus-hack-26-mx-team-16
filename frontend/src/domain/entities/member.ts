import type { MemberRole } from "@/src/domain/enums/member-role";

export interface Member {
  uuid: string;
  name: string;
  email: string;
  role: MemberRole;
  avatar?: string;
  joinedAt: string;
}

export interface MemberInvitation {
  uuid: string;
  email: string;
  role: MemberRole;
  invitedBy: string;
  expiresAt: string;
  createdAt: string;
}
