import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import type {
  DocumentTypeResponse,
  DocumentTypeListResponse,
} from "@/src/domain/responses/doctype";

export interface SuggestFieldsPayload {
  prompt?: string;
}

export interface SuggestFieldsResponse {
  datetime: string;
}

export interface CreateDocumentTypePayload {
  name: string;
  description?: string;
  isShareable?: boolean;
  slug?: string;
}

export type MissingDataHandling = "skip" | "fail" | "pass" | "ignore";

export interface ValidationRulePayload {
  id: string;
  name: string;
  prompt: string;
  enabled: boolean;
  missingHandling: MissingDataHandling;
}

export interface UpdateDocumentTypePayload {
  name?: string;
  description?: string;
  isShareable?: boolean;
  slug?: string;
  fields?: Record<string, unknown>;
  keywords?: string[];
  examples?: string[];
  validationRules?: ValidationRulePayload[];
  sampleFileId?: string;
}

export interface DocumentTypeRepository {
  getAll(workflowId?: string): Promise<DocumentTypeListResponse | ErrorFeeback>;

  getById(uuid: string): Promise<DocumentTypeResponse | ErrorFeeback>;

  create(
    payload: CreateDocumentTypePayload,
    workflowId?: string
  ): Promise<DocumentTypeResponse | ErrorFeeback>;

  update(
    uuid: string,
    payload: UpdateDocumentTypePayload
  ): Promise<DocumentTypeResponse | ErrorFeeback>;

  delete(
    uuid: string,
    workflowId?: string
  ): Promise<TaskResultResponse | ErrorFeeback>;

  suggestFields(
    uuid: string,
    payload: SuggestFieldsPayload
  ): Promise<SuggestFieldsResponse | ErrorFeeback>;
}
