/**
 * Mirror of backend WorkflowProcessingJob presenter output. The backend
 * dispatcher endpoint (`POST /v1/workflows/{workflowId}/jobs`)
 * returns a subset of these fields (setId/temporalWorkflowId/status); the
 * full shape lands in the snapshot returned by the events endpoint.
 */

import type {
  WorkflowProcessingJobStatus,
  JobStep,
} from "@/src/domain/events/processing-job-event";

export interface WorkflowProcessingJobDocument {
  uuid: string;
  name: string;
  documentTypeId: string | null;
  documentIndex: number | null;
  pageRange: { from: number; to: number } | null;
  status: string;
  processingStatus: string | null;
}

export type WorkflowProcessingJobTrigger =
  | "USER"
  | "RETRY"
  | "ORPHAN_SWEEPER"
  | "SYSTEM";

export interface WorkflowProcessingJob {
  setId: string;
  temporalWorkflowId: string;
  workflowId: string;
  workflowCaseId?: string | null;
  fileId: string;
  fileName?: string | null;
  status: WorkflowProcessingJobStatus;
  currentStep?: JobStep | null;
  lastSeq: number;
  error?: string | null;
  resultSummary?: Record<string, unknown> | null;
  trigger?: WorkflowProcessingJobTrigger;
  createdById?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  documentCount?: number;
  documents?: WorkflowProcessingJobDocument[];
}

export interface WorkflowProcessingJobDispatchResponse {
  setId: string;
  temporalWorkflowId: string;
  status: WorkflowProcessingJobStatus;
}

export interface ProcessingJobFilters {
  search?: string;
  statuses?: string; // CSV: "COMPLETED,FAILED"
  workflowCaseId?: string;
  dateFrom?: string;
  dateTo?: string;
  cursor?: string;
  limit?: number;
}

export interface ProcessingJobPage {
  data: WorkflowProcessingJob[];
  pagination: {
    nextCursor: string | null;
    limit: number;
  };
}
