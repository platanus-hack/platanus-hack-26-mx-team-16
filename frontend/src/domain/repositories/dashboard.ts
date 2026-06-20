import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { OverviewData } from "@/src/domain/entities/dashboard/overview";
import type { ProcessingData } from "@/src/domain/entities/dashboard/processing";

export interface OverviewQueryParams {
  throughputMonths?: number;
  recentLimit?: number;
}

export interface ProcessingQueryParams {
  liveLimit?: number;
}

// Response envelopes — the backend's `ApiJSONResponse` wraps the
// presenter dict in `{ data, timestamp }`, so the frontend mirrors
// that shape and unwraps in the hooks.
export interface OverviewResponse {
  data: OverviewData;
  timestamp: string;
}

export interface ProcessingResponse {
  data: ProcessingData;
  timestamp: string;
}

export interface DashboardRepository {
  getOverview(
    params?: OverviewQueryParams
  ): Promise<OverviewResponse | ErrorFeeback>;
  getProcessing(
    params?: ProcessingQueryParams
  ): Promise<ProcessingResponse | ErrorFeeback>;
}
