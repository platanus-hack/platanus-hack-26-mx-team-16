import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { handleHttpError } from "@/src/utils/http-error-handler";

export interface WorkflowDocumentPageRange {
  from: number;
  to: number;
}

/** A 4-point polygon in normalized [0..1] coordinates of the page. */
export interface MappedBboxPolygonPoint {
  x: number;
  y: number;
}

// `mapped_extraction` is wrapped in RawJson on the backend so its inner keys
// are NOT camelCased on the wire. Mirror the storage shape (snake_case)
// directly here. The outer `WorkflowDocumentDetail` keys still come through
// camelCase because that field is not RawJson — only its value is.
export interface MappedBbox {
  polygon: MappedBboxPolygonPoint[];
  confidence: number;
  page_number: number;
  matched_text: string;
}

/** Shape of every leaf in `WorkflowDocument.mapped_extraction`. */
export interface MappedField {
  value: string | number | boolean | null;
  source_text: string | null;
  page_number: number | null;
  bbox: MappedBbox[];
  /** Field-level OCR confidence, normalized to [0..1]. */
  ocr_confidence: number | null;
  inferred: boolean;
}

export type MappedExtraction = Record<string, MappedField>;

/**
 * E5 · entrada de `verification` (RawJson en el backend ⇒ claves internas en
 * snake_case, igual que `mapped_extraction`). `level`: 0=externo, 1=L1, 2=L2.
 */
export interface FieldVerificationEntry {
  value: unknown;
  verified_by: string; // "user:<uuid>" | "staff:<uuid>" | "external"
  level: number;
  verified_at: string | null;
  previous_value: unknown;
}

export type FieldVerificationMap = Record<string, FieldVerificationEntry>;

export interface WorkflowDocumentDetail {
  uuid: string;
  tenantId: string;
  caseId: string | null;
  documentTypeId: string | null;
  fileName: string | null;
  fileId: string | null;
  mimeType: string | null;
  status: string;
  source: string;
  extraction: Record<string, unknown>;
  mappedExtraction: MappedExtraction | null;
  validation: Array<Record<string, unknown>>;
  extractedText: string | null;
  extractionMetadata: Record<string, unknown>;
  pageRange: WorkflowDocumentPageRange | null;
  createdAt: string | null;
  updatedAt: string | null;
  // E5 · Inspection Bench: confianza por campo (RawJson: claves = fieldPaths),
  // campos flageados y verificación por campo. Opcionales para tolerar
  // payloads previos a E5 en caché.
  fieldConfidence?: Record<string, number> | null;
  needsClarification?: string[] | null;
  verification?: FieldVerificationMap | null;
}

export class HttpWorkflowDocumentRepository {
  constructor(private httpClient: AxiosInstance) {}

  async getById(
    documentId: string
  ): Promise<{ data: WorkflowDocumentDetail } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{
        data: WorkflowDocumentDetail;
      }>(`/v1/workflow-documents/${documentId}`);
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
