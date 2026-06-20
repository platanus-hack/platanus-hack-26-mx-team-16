import type { DocumentType } from "./doctype";

// E4 · máquina de estados pública del caso (11 estados).
// REVIEW_L1/L2 se declaran aunque solo se alcanzan a partir de E5.
export enum CaseStatus {
  RECEIVING = "RECEIVING",
  PROCESSING = "PROCESSING",
  NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION",
  NEEDS_REVIEW = "NEEDS_REVIEW",
  ANALYZING = "ANALYZING",
  REVIEW_L1 = "REVIEW_L1",
  REVIEW_L2 = "REVIEW_L2",
  COMPLETED = "COMPLETED",
  REJECTED = "REJECTED",
  FAILED = "FAILED",
  ARCHIVED = "ARCHIVED",
}

export enum CaseDocumentStatus {
  EMPTY = "EMPTY",
  UPLOADED = "UPLOADED",
  PROCESSING = "PROCESSING",
  EXTRACTED = "EXTRACTED",
  ERROR = "ERROR",
}

export enum CaseDocumentSource {
  SINGLE = "SINGLE",
  BULK = "BULK",
  // E3 · documentos virtuales: datos inyectados por API y resultados de tools.
  EXTERNAL_DATA = "EXTERNAL_DATA",
  TOOL = "TOOL",
  // E5 · fan-out: documento reasignado del padre a un child case.
  SPLIT_CHILD = "SPLIT_CHILD",
}

export interface PageRange {
  from: number;
  to: number;
}

export interface CaseDocument {
  uuid: string;
  tenantId: string;
  caseId: string;
  documentTypeId: string | null;
  fileName: string | null;
  fileId: string | null;
  status: CaseDocumentStatus;
  source: CaseDocumentSource;
  extraction: Record<string, unknown>;
  validation: Array<Record<string, unknown>>;
  extractedText: string | null;
  extractionMetadata: Record<string, unknown>;
  pageRange: PageRange | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface Case {
  uuid: string;
  tenantId: string;
  workflowUuid: string;
  name: string;
  status: CaseStatus;
  lastOcrProvider: string | null;
  createdBy: string | null;
  documentsCount: number;
  // F1 · cases-table-upload: el list endpoint ya embebe el array completo
  // (mismo presenter que el detalle). Alimenta las filas expandibles (F3).
  documents: CaseDocument[];
  createdAt: string | null;
  updatedAt: string | null;
  // E5 · fan-out: lineage del child (null si el caso no nació de un split).
  parentCaseId: string | null;
  // Re-IA 2026-06: algún run de procesamiento FAILED ⇒ badge «Procesamiento
  // fallido» en la lista (el estado público del caso no cambia).
  hasFailedRuns: boolean;
}

// E5 · fan-out: resumen de children del padre ({total, byStatus}).
export interface CaseChildrenSummary {
  total: number;
  byStatus: Partial<Record<CaseStatus, number>>;
}

export interface CaseDocumentGroup {
  documentType: DocumentType;
  documents: CaseDocument[];
}

// E4 · snapshot de completitud del expediente (completeness en await_documents.config).
export interface CaseCompletenessMissing {
  documentType: string; // doc_type slug
  missing: number;
}

export interface CaseCompleteness {
  satisfied: boolean;
  autoReady: boolean;
  readyAt: string | null;
  required: Record<string, number>; // doc_type slug -> requeridos
  present: Record<string, number>; // doc_type slug -> presentes
  missing: CaseCompletenessMissing[];
}

// E4 · evento del timeline del caso (case_events, orden desc).
export interface CaseEvent {
  uuid: string;
  type: string; // status.changed | ready | review.approved | ...
  payload: Record<string, unknown>;
  actor: string | null;
  createdAt: string;
}

export interface CaseDetail extends Case {
  documentGroups: CaseDocumentGroup[];
  // E4 · opcionales hasta que el backend los exponga en el detalle.
  timeline?: CaseEvent[];
  completeness?: CaseCompleteness | null;
  readyAt?: string | null;
  // E5 · fan-out: solo presente en el detalle de un padre con children.
  children?: CaseChildrenSummary | null;
}

export interface WorkflowCaseFilters {
  search?: string;
  statuses?: string; // CSV: "RECEIVING,PROCESSING"
  dateFrom?: string;
  dateTo?: string;
  cursor?: string;
  limit?: number;
  // E5 · fan-out: listar los children de un padre (query param parentCaseId).
  parentCaseId?: string;
  // Re-IA 2026-06: filtro «Con errores» (solo casos con runs FAILED).
  withFailedRuns?: boolean;
}

export interface WorkflowCasePage {
  data: Case[];
  pagination: {
    nextCursor: string | null;
    limit: number;
  };
}
