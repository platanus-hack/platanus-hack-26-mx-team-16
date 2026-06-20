import type { AxiosError, AxiosInstance } from "axios";

import type {
  AnalysisRun,
  AnalysisRunDetail,
  AnalysisRunEvent,
} from "@/src/domain/entities/analysis-run";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { subscribeSSE } from "@/src/infrastructure/http/sse";
import { handleHttpError } from "@/src/utils/http-error-handler";

interface RunResponse {
  data: AnalysisRun;
  datetime: string;
}

interface RunListResponse {
  data: AnalysisRun[];
  datetime: string;
}

interface RunDetailResponse {
  data: AnalysisRunDetail;
  datetime: string;
}

export interface AnalysisRunSubscription {
  unsubscribe: () => void;
}

export class HttpAnalysisRunRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async start(
    workflowId: string,
    caseId: string
  ): Promise<RunResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: AnalysisRun }>(
        `/v1/workflows/${workflowId}/cases/${caseId}/workflow-analysis-runs`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async list(
    workflowId: string,
    caseId: string
  ): Promise<RunListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: AnalysisRun[] }>(
        `/v1/workflows/${workflowId}/cases/${caseId}/workflow-analysis-runs`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async get(runId: string): Promise<RunDetailResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: AnalysisRunDetail }>(
        `/v1/workflow-analysis-runs/${runId}`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async cancel(runId: string): Promise<RunResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: AnalysisRun }>(
        `/v1/workflow-analysis-runs/${runId}/cancel`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async forceCancel(runId: string): Promise<RunResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: AnalysisRun }>(
        `/v1/workflow-analysis-runs/${runId}/force-cancel`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  /**
   * Subscribe to the live SSE stream for a run. Reuses the project's
   * `subscribeSSE` helper which handles auth headers + reconnection.
   */
  subscribe(
    runId: string,
    onEvent: (event: AnalysisRunEvent) => void,
    onError?: (err: unknown) => void
  ): AnalysisRunSubscription {
    const url = `/api/v1/workflow-analysis-runs/${runId}/events`; // renamed per spec §11
    const cleanup = subscribeSSE(() => url, {
      onEvent: (raw) => {
        if (!raw.data || raw.data === "{}") return;
        try {
          const parsed = JSON.parse(raw.data) as AnalysisRunEvent;
          onEvent(parsed);
        } catch (err) {
          onError?.(err);
        }
      },
      onError,
    });
    return { unsubscribe: cleanup };
  }
}
