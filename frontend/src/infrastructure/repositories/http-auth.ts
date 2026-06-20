import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { AuthRepository } from "@/src/domain/repositories/auth";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { TenantUserSessionResponse } from "@/src/domain/responses/tenant-user-session";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpAuthRepository implements AuthRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async login(
    email: string,
    password: string
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { email, password };
    try {
      const httpResponse = await this.httpClient.post("/auth/login", payload);
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async logout(
    refreshToken?: string | null
  ): Promise<TaskResultResponse | ErrorFeeback> {
    const payload = { refreshToken };
    try {
      const response = await this.httpClient.post("/auth/logout", payload);
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async googleLogin(
    code: string
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { code };
    try {
      const httpResponse = await this.httpClient.post(
        "/auth/google-login",
        payload
      );
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async refresh(
    refreshToken?: string | null
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { refreshToken };
    try {
      const httpResponse = await this.httpClient.post("/auth/refresh", payload);
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
