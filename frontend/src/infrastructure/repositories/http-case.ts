import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CaseRepository,
  CreateCasePayload,
  UpdateCasePayload,
  UploadedFile,
} from "@/src/domain/repositories/case";
import type {
  CaseDetailResponse,
  CaseListResponse,
  CaseResponse,
} from "@/src/domain/responses/case";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type {
  Case,
  CaseCompleteness,
  CaseDetail,
  CaseDocument,
  CaseDocumentGroup,
  CaseEvent,
  WorkflowCaseFilters,
  WorkflowCasePage,
} from "@/src/domain/entities/case";
import {
  CaseDocumentSource,
  type CaseDocumentStatus,
} from "@/src/domain/entities/case";
import type { DocumentType } from "@/src/domain/entities/doctype";
import { successTask } from "@/src/domain/responses/task-result";
import { handleHttpError } from "@/src/utils/http-error-handler";

interface BackendCaseDocument {
  uuid: string;
  tenantId: string;
  caseId: string;
  documentTypeId: string | null;
  fileName: string | null;
  fileId: string | null;
  status: string;
  source: string;
  extraction: Record<string, unknown>;
  validation: Array<Record<string, unknown>>;
  extractedText: string | null;
  extractionMetadata: Record<string, unknown>;
  pageRange: { from: number; to: number } | null;
  createdAt: string | null;
  updatedAt: string | null;
}

interface BackendDocumentGroup {
  documentType: DocumentType;
  documents: BackendCaseDocument[];
}

interface BackendCase {
  uuid: string;
  tenantId: string;
  workflowId: string;
  name: string;
  status: string;
  lastOcrProvider: string | null;
  createdBy: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  hasFailedRuns?: boolean;
  documents?: BackendCaseDocument[];
  documentGroups?: BackendDocumentGroup[];
  // E4 · expediente formal (presentes solo en el detalle).
  timeline?: BackendCaseEvent[];
  completeness?: CaseCompleteness | null;
  readyAt?: string | null;
  // E5 · fan-out: lineage + resumen de children (children solo en el detalle).
  parentCaseId?: string | null;
  children?: {
    total: number;
    byStatus: Record<string, number>;
  } | null;
}

interface BackendCaseEvent {
  uuid: string;
  type: string;
  payload: Record<string, unknown> | null;
  actor: string | null;
  createdAt: string;
}

function countDocuments(raw: BackendCase): number {
  if (raw.documentGroups) {
    return raw.documentGroups.reduce((acc, g) => acc + g.documents.length, 0);
  }
  return (raw.documents ?? []).length;
}

function mapCase(raw: BackendCase): Case {
  return {
    uuid: raw.uuid,
    tenantId: raw.tenantId,
    workflowUuid: raw.workflowId,
    name: raw.name,
    status: raw.status as Case["status"],
    lastOcrProvider: raw.lastOcrProvider,
    createdBy: raw.createdBy,
    documentsCount: countDocuments(raw),
    documents: (raw.documents ?? []).map(mapCaseDocument),
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
    parentCaseId: raw.parentCaseId ?? null,
    hasFailedRuns: raw.hasFailedRuns ?? false,
  };
}

function mapCaseDocument(raw: BackendCaseDocument): CaseDocument {
  return {
    uuid: raw.uuid,
    tenantId: raw.tenantId,
    caseId: raw.caseId,
    documentTypeId: raw.documentTypeId,
    fileName: raw.fileName,
    fileId: raw.fileId,
    status: raw.status as CaseDocumentStatus,
    source: (raw.source as CaseDocumentSource) ?? CaseDocumentSource.SINGLE,
    extraction: raw.extraction ?? {},
    validation: raw.validation ?? [],
    extractedText: raw.extractedText,
    extractionMetadata: raw.extractionMetadata ?? {},
    pageRange: raw.pageRange,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
  };
}

function mapDocumentGroup(raw: BackendDocumentGroup): CaseDocumentGroup {
  return {
    documentType: raw.documentType,
    documents: raw.documents.map(mapCaseDocument),
  };
}

function mapCaseEvent(raw: BackendCaseEvent): CaseEvent {
  return {
    uuid: raw.uuid,
    type: raw.type,
    payload: raw.payload ?? {},
    actor: raw.actor ?? null,
    createdAt: raw.createdAt,
  };
}

function mapCaseDetail(raw: BackendCase): CaseDetail {
  const documentGroups = (raw.documentGroups ?? []).map(mapDocumentGroup);
  return {
    ...mapCase(raw),
    // El detalle viaja como documentGroups; aplanamos para el `documents` plano
    // que `Case` declara (la lista sí trae `raw.documents`).
    documents: documentGroups.flatMap((g) => g.documents),
    documentGroups,
    timeline: (raw.timeline ?? []).map(mapCaseEvent),
    completeness: raw.completeness ?? null,
    readyAt: raw.readyAt ?? null,
    children: (raw.children as CaseDetail["children"]) ?? null,
  };
}

export class HttpCaseRepository implements CaseRepository {
  private httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(workflowUuid: string): Promise<CaseListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: BackendCase[] }>(
        `/v1/workflows/${workflowUuid}/cases`
      );
      return {
        data: response.data.data.map(mapCase),
        datetime: new Date().toISOString(),
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getPaginated(
    workflowUuid: string,
    filters?: WorkflowCaseFilters
  ): Promise<WorkflowCasePage | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{
        data: BackendCase[];
        pagination: { nextCursor: string | null; limit: number };
      }>(`/v1/workflows/${workflowUuid}/cases`, { params: filters });
      return {
        data: response.data.data.map(mapCase),
        pagination: response.data.pagination,
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(
    workflowUuid: string,
    caseUuid: string
  ): Promise<CaseDetailResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: BackendCase }>(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}`
      );
      return {
        data: mapCaseDetail(response.data.data),
        datetime: new Date().toISOString(),
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    workflowUuid: string,
    payload: CreateCasePayload
  ): Promise<CaseResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: BackendCase }>(
        `/v1/workflows/${workflowUuid}/cases`,
        payload
      );
      return {
        data: mapCase(response.data.data),
        datetime: new Date().toISOString(),
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    workflowUuid: string,
    caseUuid: string,
    payload: UpdateCasePayload
  ): Promise<CaseResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: BackendCase }>(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}`,
        payload
      );
      return {
        data: mapCase(response.data.data),
        datetime: new Date().toISOString(),
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(
    workflowUuid: string,
    caseUuid: string
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      await this.httpClient.delete(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}`
      );
      return successTask;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async uploadFile(file: File): Promise<{ data: UploadedFile } | ErrorFeeback> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await this.httpClient.post<{ data: UploadedFile }>(
        "/v1/documents/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async createCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    payload: { fileId: string; fileName: string; documentTypeId: string }
  ): Promise<{ data: CaseDocument } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{
        data: BackendCaseDocument;
      }>(`/v1/workflows/${workflowUuid}/cases/${caseUuid}/documents`, payload);
      return { data: mapCaseDocument(response.data.data) };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async deleteCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      await this.httpClient.delete(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}/documents/${documentUuid}`
      );
      return successTask;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async updateCaseDocument(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string,
    payload: { fileName?: string }
  ): Promise<{ data: CaseDocument } | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: BackendCaseDocument }>(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}/documents/${documentUuid}`,
        payload
      );
      return { data: mapCaseDocument(response.data.data) };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getFilePresignedUrl(
    fileId: string
  ): Promise<{ data: UploadedFile } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: UploadedFile }>(
        `/v1/documents/${fileId}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async startCaseDocumentExtraction(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string
  ): Promise<{ data: ExtractionStartResponse } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<
        { data?: ExtractionStartResponse } & ExtractionStartResponse
      >(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}/documents/${documentUuid}/extract`
      );
      const payload =
        response.data.data ?? (response.data as ExtractionStartResponse);
      return { data: payload };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getCaseDocumentExtractionStatus(
    workflowUuid: string,
    caseUuid: string,
    documentUuid: string
  ): Promise<{ data: ExtractionStatusResponse } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<
        { data?: ExtractionStatusResponse } & ExtractionStatusResponse
      >(
        `/v1/workflows/${workflowUuid}/cases/${caseUuid}/documents/${documentUuid}/extract/status`
      );
      const payload =
        response.data.data ?? (response.data as ExtractionStatusResponse);
      return { data: payload };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  /**
   * Bulk: dispatch a processing-job against the unified workflow endpoint.
   * Replaces the legacy `POST /v1/workflows/{wf}/cases/{case}/files/{file}/extract`.
   */
  async startCaseFileExtraction(
    workflowUuid: string,
    caseUuid: string,
    fileId: string
  ): Promise<{ data: JobDispatchResponse } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<
        {
          data?: BackendDispatchResponse;
        } & BackendDispatchResponse
      >(`/v1/workflows/${workflowUuid}/jobs`, {
        fileId,
        workflowCaseId: caseUuid,
      });
      const payload =
        response.data.data ?? (response.data as BackendDispatchResponse);
      return {
        data: {
          jobId: payload.setId,
          status: "dispatched",
          setId: payload.setId,
          temporalWorkflowId: payload.temporalWorkflowId,
        },
      };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}

interface BackendDispatchResponse {
  setId: string;
  temporalWorkflowId: string;
  status: string;
}

export interface ExtractionStartResponse {
  workflowId?: string;
  jobId: string;
  status: "started" | "already_running" | "dispatched";
  mode?: "bulk_reextract";
}

export interface JobDispatchResponse {
  jobId: string;
  status: "dispatched";
  setId: string;
  temporalWorkflowId: string;
}

export interface ExtractionStatusResponse {
  workflowId: string;
  status: string;
  done?: boolean;
  result?: unknown;
  error?: string;
}
