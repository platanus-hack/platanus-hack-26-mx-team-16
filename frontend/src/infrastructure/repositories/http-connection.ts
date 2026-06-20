import type { AxiosError, AxiosInstance } from "axios";
import type {
  ConnectionAccount,
  CreateConnectionPayload,
} from "@/src/domain/entities/connection";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { handleHttpError } from "@/src/utils/http-error-handler";

/**
 * Org-level connection accounts. Goes through the middleware proxy
 * (`/api/v1/*` → backend with `X-Api-Key`) via `authHttp`.
 */
export class HttpConnectionRepository {
  private httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance = authHttp) {
    this.httpClient = httpClient;
  }

  async list(): Promise<{ data: ConnectionAccount[] } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: ConnectionAccount[] }>(
        "/v1/connections"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    payload: CreateConnectionPayload
  ): Promise<{ data: ConnectionAccount } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: ConnectionAccount }>(
        "/v1/connections",
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async remove(uuid: string): Promise<{ deleted: boolean } | ErrorFeeback> {
    try {
      await this.httpClient.delete(`/v1/connections/${uuid}`);
      return { deleted: true };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
