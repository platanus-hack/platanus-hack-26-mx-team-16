import type { AxiosError, AxiosInstance } from "axios";

import type { RunSummary, WorkflowSynthesisConfig } from "@/src/domain/entities/run-summary";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  RunSummaryRepository,
  UpdateSynthesisConfigPayload,
} from "@/src/domain/repositories/run-summary";
import type {
  RunSummaryResponse,
  WorkflowSynthesisConfigResponse,
} from "@/src/domain/responses/run-summary";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpRunSummaryRepository implements RunSummaryRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async getByRunId(runId: string): Promise<RunSummaryResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: RunSummary }>(
        `/v1/workflow-analysis-runs/${runId}/summary`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async resynthesize(
    runId: string,
    force = false
  ): Promise<RunSummaryResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: RunSummary }>(
        `/v1/workflow-analysis-runs/${runId}/summary/resynthesize`,
        null,
        { params: { force } }
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getWorkflowConfig(
    workflowId: string
  ): Promise<WorkflowSynthesisConfigResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowSynthesisConfig }>(
        `/v1/workflows/${workflowId}/output-schema`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updateWorkflowConfig(
    workflowId: string,
    payload: UpdateSynthesisConfigPayload
  ): Promise<WorkflowSynthesisConfigResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: WorkflowSynthesisConfig }>(
        `/v1/workflows/${workflowId}/output-schema`,
        payload
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
