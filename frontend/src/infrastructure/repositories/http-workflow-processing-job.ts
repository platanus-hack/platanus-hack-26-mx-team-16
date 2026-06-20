import type { AxiosError, AxiosInstance } from "axios";

import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  WorkflowProcessingJob,
  WorkflowProcessingJobDispatchResponse,
  WorkflowProcessingJobDocument,
  ProcessingJobFilters,
  ProcessingJobPage,
} from "@/src/domain/entities/workflow-processing-job";
import type {
  DeleteWorkflowProcessingJobPayload,
  DispatchWorkflowProcessingJobPayload,
  ListWorkflowProcessingJobsPayload,
  ReExtractCaseFieldsPayload,
  ReExtractCaseFieldsResponse,
  WorkflowProcessingJobListResponse,
  WorkflowProcessingJobRepository,
} from "@/src/domain/repositories/workflow-processing-job-repository";
import { handleHttpError } from "@/src/utils/http-error-handler";

interface BackendDispatchResponse {
  setId: string;
  temporalWorkflowId: string;
  status: WorkflowProcessingJobDispatchResponse["status"];
}

interface BackendProcessingJob {
  setId: string;
  temporalWorkflowId: string;
  workflowId: string;
  workflowCaseId: string | null;
  fileId: string;
  fileName: string | null;
  status: WorkflowProcessingJob["status"];
  currentStep: WorkflowProcessingJob["currentStep"];
  lastSeq: number;
  error: string | null;
  resultSummary: Record<string, unknown> | null;
  createdAt: string | null;
  updatedAt: string | null;
  documentCount?: number;
  documents?: WorkflowProcessingJobDocument[];
}

function mapProcessingJob(raw: BackendProcessingJob): WorkflowProcessingJob {
  return {
    setId: raw.setId,
    temporalWorkflowId: raw.temporalWorkflowId,
    workflowId: raw.workflowId,
    workflowCaseId: raw.workflowCaseId,
    fileId: raw.fileId,
    fileName: raw.fileName ?? null,
    status: raw.status,
    currentStep: raw.currentStep ?? null,
    lastSeq: raw.lastSeq ?? 0,
    error: raw.error,
    resultSummary: raw.resultSummary,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
    documentCount: raw.documentCount ?? raw.documents?.length ?? 0,
    documents: raw.documents ?? [],
  };
}

export class HttpWorkflowProcessingJobRepository
  implements WorkflowProcessingJobRepository
{
  private httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async dispatch(
    payload: DispatchWorkflowProcessingJobPayload
  ): Promise<{ data: WorkflowProcessingJobDispatchResponse } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{
        data: BackendDispatchResponse;
      }>(`/v1/workflows/${payload.workflowId}/jobs`, {
        fileId: payload.fileId,
        workflowCaseId: payload.workflowCaseId,
      });
      return {
        data: {
          setId: response.data.data.setId,
          temporalWorkflowId: response.data.data.temporalWorkflowId,
          status: response.data.data.status,
        },
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(
    payload: DeleteWorkflowProcessingJobPayload
  ): Promise<{ data: { status: string } } | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<{
        data: { status: string };
      }>(
        `/v1/workflows/${payload.workflowId}/jobs/${payload.processingJobId}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  // Re-IA 2026-06: «Reintentar» de un run FAILED desde la Actividad del caso.
  async retry(payload: {
    workflowId: string;
    processingJobId: string;
  }): Promise<{ data: { status: string } } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{
        data: { status: string };
      }>(
        `/v1/workflows/${payload.workflowId}/jobs/${payload.processingJobId}/retry`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async reExtractCaseFields(
    payload: ReExtractCaseFieldsPayload
  ): Promise<{ data: ReExtractCaseFieldsResponse } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{
        data: ReExtractCaseFieldsResponse;
      }>(
        `/v1/workflows/${payload.workflowId}/cases/${payload.caseId}/jobs/re-extract`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async list(
    payload: ListWorkflowProcessingJobsPayload
  ): Promise<WorkflowProcessingJobListResponse | ErrorFeeback> {
    try {
      const params: Record<string, string | number> = {};
      if (payload.workflowCaseId)
        params.workflowCaseId = payload.workflowCaseId;
      if (payload.page !== undefined) params.page = payload.page;

      const response = await this.httpClient.get<{
        data: BackendProcessingJob[];
      }>(`/v1/workflows/${payload.workflowId}/jobs`, { params });

      return {
        data: response.data.data.map(mapProcessingJob),
        page: payload.page ?? 1,
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listPaginated(
    workflowId: string,
    filters?: ProcessingJobFilters
  ): Promise<ProcessingJobPage | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{
        data: BackendProcessingJob[];
        pagination: { nextCursor: string | null; limit: number };
      }>(`/v1/workflows/${workflowId}/jobs`, { params: filters });
      return {
        data: response.data.data.map(mapProcessingJob),
        pagination: response.data.pagination,
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
