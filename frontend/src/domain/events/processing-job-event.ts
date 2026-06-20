/**
 * Mirror of backend `src/common/domain/enums/case_events.py` after the
 * unification rename. Event types travel from the Temporal workflow via
 * Redis Pub/Sub to the browser SSE consumer.
 */

export const ProcessingJobEventType = {
  Dispatched: "processing_job.dispatched",
  StepStarted: "processing_job.step_started",
  StepCompleted: "processing_job.step_completed",
  Completed: "processing_job.completed",
  Failed: "processing_job.failed",
  DocumentPersisted: "processing_job.document_persisted",
} as const;

export type ProcessingJobEventType =
  (typeof ProcessingJobEventType)[keyof typeof ProcessingJobEventType];

export const JobStep = {
  ExtractText: "extract_text",
  ClassifyPages: "classify_pages",
  PersistDocs: "persist_documents",
  ExtractFields: "extract_fields",
  Validate: "validate_extraction",
} as const;

export type JobStep = (typeof JobStep)[keyof typeof JobStep];

export const WorkflowProcessingJobStatus = {
  PENDING: "PENDING",
  RUNNING: "RUNNING",
  PROCESSING: "PROCESSING",
  COMPLETED: "COMPLETED",
  PARTIAL: "PARTIAL",
  FAILED: "FAILED",
} as const;

export type WorkflowProcessingJobStatus =
  (typeof WorkflowProcessingJobStatus)[keyof typeof WorkflowProcessingJobStatus];

const IN_FLIGHT_SET_STATUSES = new Set<WorkflowProcessingJobStatus>([
  WorkflowProcessingJobStatus.PENDING,
  WorkflowProcessingJobStatus.PROCESSING,
]);

const TERMINAL_SET_STATUSES = new Set<WorkflowProcessingJobStatus>([
  WorkflowProcessingJobStatus.COMPLETED,
  WorkflowProcessingJobStatus.PARTIAL,
  WorkflowProcessingJobStatus.FAILED,
]);

export function isWorkflowProcessingJobInFlight(
  status: WorkflowProcessingJobStatus
): boolean {
  return IN_FLIGHT_SET_STATUSES.has(status);
}

export function isWorkflowProcessingJobTerminal(
  status: WorkflowProcessingJobStatus
): boolean {
  return TERMINAL_SET_STATUSES.has(status);
}

export const DocumentStatus = {
  Pending: "pending",
  Extracting: "extracting",
  Validating: "validating",
  Completed: "completed",
  Failed: "failed",
} as const;

export type DocumentStatus =
  (typeof DocumentStatus)[keyof typeof DocumentStatus];

/**
 * Wire envelope for every SSE event. Field naming mirrors the backend
 * presenter (camelCase). The backend wraps a typed payload that varies
 * per `type`; consumers should narrow on `type` before reading payload.
 */
export interface ProcessingJobEventEnvelope<P = Record<string, unknown>> {
  seq: number;
  ts: string;
  type: ProcessingJobEventType;
  workflowId: string;
  processingJobId: string;
  workflowCaseId?: string | null;
  documentId?: string | null;
  payload: P;
}

export interface PersistedDocumentRefDTO {
  documentId: string;
  documentTypeId: string | null;
  documentTypeName: string | null;
  documentIndex: number;
  pageRange: { from: number; to: number };
}
