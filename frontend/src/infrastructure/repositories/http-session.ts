import type { AxiosError, AxiosInstance } from "axios";
import type { TenantUserContext } from "@/src/domain/entities/auth/tenant-user-session";
import type { RequestContext } from "@/src/domain/entities/common/request-context";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { SessionRepository } from "@/src/domain/repositories/session";
import type { TenantUserSessionResponse } from "@/src/domain/responses/tenant-user-session";
import { getCommonHeaders } from "@/src/infrastructure/requests";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpSessionRepository implements SessionRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async getSession(
    context: RequestContext
  ): Promise<TenantUserContext | ErrorFeeback> {
    try {
      const headers = getCommonHeaders(
        context.tenant ?? null,
        context.accessToken ?? null
      );
      const response = await this.httpClient.get<{ data: TenantUserContext }>(
        "/auth/session",
        {
          headers,
        }
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) ?? genericServerError;
    }
  }

  async logout(): Promise<TenantUserSessionResponse | ErrorFeeback> {
    return genericServerError;
  }
}
