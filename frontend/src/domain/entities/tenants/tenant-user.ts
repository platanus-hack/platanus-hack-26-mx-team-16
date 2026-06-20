export interface TenantUserEmailAddress {
  uuid: string;
  email: string;
  isVerified: boolean;
}

export interface TenantUserRole {
  uuid: string;
  name: string;
  status: string;
}

export interface TenantUser {
  uuid: string;
  firstName: string | null;
  lastName: string | null;
  emailAddress: TenantUserEmailAddress | null;
  phoneNumber: object | null;
  isOwner: boolean;
  isSupport: boolean;
  photoUrl: string | null;
  status: string;
  tenantRole: TenantUserRole | null;
  createdAt: string;
}
