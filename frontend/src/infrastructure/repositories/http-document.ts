import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { DocumentRepository } from "@/src/domain/repositories/document";
import type {
  DocumentResponse,
  DocumentListResponse,
} from "@/src/domain/responses/document";
import type { Document } from "@/src/domain/entities/document";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpDocumentRepository implements DocumentRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(
    workflowUuid: string
  ): Promise<DocumentListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: Document[] }>(
        `/v1/workflows/${workflowUuid}/documents`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(uuid: string): Promise<DocumentResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: Document }>(
        `/v1/documents/${uuid}`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<TaskResultResponse>(
        `/v1/documents/${uuid}`
      );
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
