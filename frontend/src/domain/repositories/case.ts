import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CaseDetailResponse,
  CaseListResponse,
  CaseResponse,
} from "@/src/domain/responses/case";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type { CaseDocument, WorkflowCaseFilters, WorkflowCasePage } from "@/src/domain/entities/case";

export interface CreateCasePayload {
  name: string;
}

export interface UpdateCasePayload {
  name?: string;
  status?: string;
}

export interface UploadedFile {
  uuid: string;
  fileName: string;
  mime: string;
  size: number;
  s3Key: string;
  presignedUrl: string | null;
}

export interface CaseRepository {
  getAll(workflowUuid: string): Promise<CaseListResponse | ErrorFeeback>;
  getPaginated(
    workflowUuid: string,
    filters?: WorkflowCaseFilters
  ): Promise<WorkflowCasePage | ErrorFeeback>;
  getById(
    workflowUuid: string,
    caseUuid: string
  ): Promise<CaseDetailResponse | ErrorFeeback>;
  create(
    workflowUuid: string,
    payload: CreateCasePayload
  ): Promise<CaseResponse | ErrorFeeback>;
  update(
    workflowUuid: string,
    caseUuid: string,
    payload: UpdateCasePayload
  ): Promise<CaseResponse | ErrorFeeback>;
  delete(
    workflowUuid: string,
    caseUuid: string
  ): Promise<TaskResultResponse | ErrorFeeback>;
  uploadFile(file: File): Promise<{ data: UploadedFile } | ErrorFeeback>;
  createCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    payload: { fileId: string; fileName: string; documentTypeId: string }
  ): Promise<{ data: CaseDocument } | ErrorFeeback>;
  deleteCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string
  ): Promise<TaskResultResponse | ErrorFeeback>;
  updateCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string,
    payload: { fileName?: string }
  ): Promise<{ data: CaseDocument } | ErrorFeeback>;
  getFilePresignedUrl(
    fileId: string
  ): Promise<{ data: UploadedFile } | ErrorFeeback>;
}
