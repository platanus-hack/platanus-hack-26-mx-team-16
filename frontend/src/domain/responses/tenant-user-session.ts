import type {
  TenantUserProfile,
  TenantUserSession,
} from "@/src/domain/entities/auth/tenant-user-session";

export interface TenantUserSessionResponse {
  data: TenantUserSession;
  datetime: string;
}

export interface TenantUserProfileResponse {
  data: TenantUserProfile;
  datetime: string;
}
