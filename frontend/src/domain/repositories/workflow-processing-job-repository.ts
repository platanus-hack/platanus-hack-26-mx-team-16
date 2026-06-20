import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  WorkflowProcessingJob,
  WorkflowProcessingJobDispatchResponse,
  ProcessingJobFilters,
  ProcessingJobPage,
} from "@/src/domain/entities/workflow-processing-job";

export interface DispatchWorkflowProcessingJobPayload {
  workflowId: string;
  fileId: string;
  workflowCaseId?: string;
}

export interface ListWorkflowProcessingJobsPayload {
  workflowId: string;
  workflowCaseId?: string;
  page?: number;
}

export interface WorkflowProcessingJobListResponse {
  data: WorkflowProcessingJob[];
  page: number;
  total?: number;
}

export interface DeleteWorkflowProcessingJobPayload {
  workflowId: string;
  processingJobId: string;
}

export interface ReExtractCaseFieldsPayload {
  workflowId: string;
  caseId: string;
}

export interface ReExtractCaseFieldsResponse {
  caseId: string;
  workflowId: string;
  dispatched: { setId: string; jobId: string }[];
}

export interface WorkflowProcessingJobRepository {
  dispatch(
    payload: DispatchWorkflowProcessingJobPayload
  ): Promise<{ data: WorkflowProcessingJobDispatchResponse } | ErrorFeeback>;

  list(
    payload: ListWorkflowProcessingJobsPayload
  ): Promise<WorkflowProcessingJobListResponse | ErrorFeeback>;

  listPaginated(
    workflowId: string,
    filters?: ProcessingJobFilters
  ): Promise<ProcessingJobPage | ErrorFeeback>;

  delete(
    payload: DeleteWorkflowProcessingJobPayload
  ): Promise<{ data: { status: string } } | ErrorFeeback>;

  reExtractCaseFields(
    payload: ReExtractCaseFieldsPayload
  ): Promise<{ data: ReExtractCaseFieldsResponse } | ErrorFeeback>;
}
