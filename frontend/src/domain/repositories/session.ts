import type { TenantUserContext } from "@/src/domain/entities/auth/tenant-user-session";
import type { RequestContext } from "@/src/domain/entities/common/request-context";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { TenantUserSessionResponse } from "@/src/domain/responses/tenant-user-session";

export interface SessionRepository {
  getSession(
    context: RequestContext
  ): Promise<TenantUserContext | ErrorFeeback>;
  logout(): Promise<TenantUserSessionResponse | ErrorFeeback>;
}
