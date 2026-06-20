import type { AxiosError, AxiosInstance } from "axios";

import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  DashboardRepository,
  OverviewQueryParams,
  OverviewResponse,
  ProcessingQueryParams,
  ProcessingResponse,
} from "@/src/domain/repositories/dashboard";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpDashboardRepository implements DashboardRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getOverview(
    params: OverviewQueryParams = {}
  ): Promise<OverviewResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<OverviewResponse>(
        "/v1/dashboard/overview",
        {
          params: {
            throughputMonths: params.throughputMonths,
            recentLimit: params.recentLimit,
          },
        }
      );
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getProcessing(
    params: ProcessingQueryParams = {}
  ): Promise<ProcessingResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<ProcessingResponse>(
        "/v1/dashboard/processing",
        {
          params: { liveLimit: params.liveLimit },
        }
      );
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
