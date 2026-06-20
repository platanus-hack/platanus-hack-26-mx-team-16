import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { TenantUserSessionResponse } from "@/src/domain/responses/tenant-user-session";

export interface AuthRepository {
  login(
    email: string | unknown,
    password: string | unknown
  ): Promise<TenantUserSessionResponse | ErrorFeeback>;

  logout(
    refreshToken?: string | null
  ): Promise<TaskResultResponse | ErrorFeeback>;

  refresh(
    refreshToken?: string | null
  ): Promise<TenantUserSessionResponse | ErrorFeeback>;

  googleLogin(code: string): Promise<TenantUserSessionResponse | ErrorFeeback>;
}
