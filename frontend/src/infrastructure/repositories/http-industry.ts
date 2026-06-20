import type { AxiosError, AxiosInstance } from "axios";

import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { Industry } from "@/src/domain/entities/industry";
import type { IndustryRepository } from "@/src/domain/repositories/industry";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpIndustryRepository implements IndustryRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async list(): Promise<Industry[] | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: Industry[] }>(
        "/v1/industries",
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
