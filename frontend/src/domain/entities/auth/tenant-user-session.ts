import type { JwtSession } from "@/src/domain/entities/auth/jwt-session";
import { emptyJwtSession } from "@/src/domain/entities/auth/jwt-session";
import type { Tenant } from "@/src/domain/entities/tenant";
import { emptyTenant } from "@/src/domain/entities/tenant";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import { emptyTenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { User } from "@/src/domain/entities/user";
import { emptyUser } from "@/src/domain/entities/user";

export interface TenantUserProfile {
  user: User;
  tenant: Tenant | null;
}

export const emptyTenantUserProfile: TenantUserProfile = {
  user: emptyUser,
  tenant: emptyTenant,
};

export interface TenantUserSession {
  session: JwtSession;
  user: User;
  tenant: Tenant | null;
  tenantRole: TenantRole | null;
}

export const emptyTenantUserSession: TenantUserSession = {
  session: emptyJwtSession,
  user: emptyUser,
  tenant: emptyTenant,
  tenantRole: emptyTenantRole,
};

export type TenantUserContext = Omit<TenantUserSession, "session">;

export const emptyTenantUserContext: TenantUserContext = {
  user: emptyUser,
  tenant: emptyTenant,
  tenantRole: emptyTenantRole,
};
