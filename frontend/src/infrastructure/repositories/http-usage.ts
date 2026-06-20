import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  ProcessRecordsFilters,
  UsageSummaryResponse,
  UsageRepository,
} from "@/src/domain/repositories/usage";
import type { ProcessRecord, ProcessRecordPage, UsageSummary } from "@/src/domain/entities/usage";
import { handleHttpError } from "@/src/utils/http-error-handler";

interface ProcessRecordsApiResponse {
  data: ProcessRecord[];
  pagination: { nextCursor: string | null; limit: number };
}

export class HttpUsageRepository implements UsageRepository {
  constructor(private httpClient: AxiosInstance) {}

  async getSummary(): Promise<UsageSummaryResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: UsageSummary }>(
        "/v1/usage/summary"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async filter(
    filters?: ProcessRecordsFilters
  ): Promise<ProcessRecordPage | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<ProcessRecordsApiResponse>(
        "/v1/usage/process-records",
        {
          params: {
            fromDt: filters?.fromDt,
            toDt: filters?.toDt,
            limit: filters?.limit ?? 25,
            cursor: filters?.cursor,
          },
        }
      );
      return {
        data: response.data.data,
        pagination: response.data.pagination,
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
