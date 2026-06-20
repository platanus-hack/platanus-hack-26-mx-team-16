import type { Member, MemberInvitation } from "@/src/domain/entities/member";

export interface MemberResponse {
  data: Member;
  datetime: string;
}

export interface MemberListResponse {
  data: Member[];
  datetime: string;
}

export interface MemberInvitationResponse {
  data: MemberInvitation;
  datetime: string;
}

export interface MemberInvitationListResponse {
  data: MemberInvitation[];
  datetime: string;
}

export interface MembersWithInvitationsResponse {
  members: Member[];
  invitations: MemberInvitation[];
  datetime: string;
}
