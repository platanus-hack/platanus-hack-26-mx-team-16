import type { AxiosError, AxiosInstance } from "axios";
import { authHttp } from "@/src/infrastructure/http/client";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CreateDocumentTypePayload,
  DocumentTypeRepository,
  SuggestFieldsPayload,
  SuggestFieldsResponse,
  UpdateDocumentTypePayload,
} from "@/src/domain/repositories/doctype";
import type {
  DocumentTypeListResponse,
  DocumentTypeResponse,
} from "@/src/domain/responses/doctype";
import type { DocumentType } from "@/src/domain/entities/doctype";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpDocumentTypeRepository implements DocumentTypeRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(
    workflowId?: string
  ): Promise<DocumentTypeListResponse | ErrorFeeback> {
    try {
      const url = workflowId
        ? `/v1/workflows/${workflowId}/document-types`
        : "/v1/document-types";
      const response = await this.httpClient.get<{ data: DocumentType[] }>(url);
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(uuid: string): Promise<DocumentTypeResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: DocumentType }>(
        `/v1/document-types/${uuid}`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    payload: CreateDocumentTypePayload,
    workflowId?: string
  ): Promise<DocumentTypeResponse | ErrorFeeback> {
    try {
      const url = workflowId
        ? `/v1/workflows/${workflowId}/document-types`
        : "/v1/document-types";
      const response = await this.httpClient.post<{ data: DocumentType }>(
        url,
        payload
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    uuid: string,
    payload: UpdateDocumentTypePayload
  ): Promise<DocumentTypeResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: DocumentType }>(
        `/v1/document-types/${uuid}`,
        payload
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(
    uuid: string,
    workflowId?: string
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      const url = workflowId
        ? `/v1/workflows/${workflowId}/document-types/${uuid}`
        : `/v1/document-types/${uuid}`;
      const response = await this.httpClient.delete<TaskResultResponse>(url);
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async suggestFields(
    uuid: string,
    payload: SuggestFieldsPayload
  ): Promise<SuggestFieldsResponse | ErrorFeeback> {
    try {
      await this.httpClient.post(
        `/v1/document-types/${uuid}/suggest-fields`,
        payload
      );
      return { datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}

export const httpDocumentTypeRepository = new HttpDocumentTypeRepository(
  authHttp
);
