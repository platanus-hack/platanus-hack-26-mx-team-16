import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { ProcessRecordPage, UsageSummary } from "@/src/domain/entities/usage";

export interface ProcessRecordsFilters {
  fromDt?: string;
  toDt?: string;
  cursor?: string;
  limit?: number;
}

export interface UsageSummaryResponse {
  data: UsageSummary;
}

export interface UsageRepository {
  getSummary(): Promise<UsageSummaryResponse | ErrorFeeback>;
  filter(
    filters?: ProcessRecordsFilters
  ): Promise<ProcessRecordPage | ErrorFeeback>;
}
