import type { AxiosError, AxiosInstance } from "axios";

import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  ProfileRepository,
  UpdatePasswordPayload,
  UpdateProfilePayload,
} from "@/src/domain/repositories/profile";
import type { UserResponse } from "@/src/domain/responses/profile";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { User } from "@/src/domain/entities/user";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpProfileRepository implements ProfileRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async get(): Promise<UserResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: User }>(
        "/v1/me/profile"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    payload: UpdateProfilePayload
  ): Promise<UserResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: User }>(
        "/v1/me/profile",
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updatePassword(
    payload: UpdatePasswordPayload
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<TaskResultResponse>(
        "/v1/me/password",
        payload
      );
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
