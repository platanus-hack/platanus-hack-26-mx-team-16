import type { AxiosError, AxiosInstance } from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { KnowledgeDocument } from "@/src/domain/entities/knowledge-document";
import type { KnowledgeDocumentRepository } from "@/src/domain/repositories/knowledge-document";
import type {
  KnowledgeDocumentListResponse,
  KnowledgeDocumentResponse,
} from "@/src/domain/responses/knowledge-document";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import { successTask } from "@/src/domain/responses/task-result";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpKnowledgeDocumentRepository
  implements KnowledgeDocumentRepository
{
  constructor(private readonly httpClient: AxiosInstance) {}

  async getAll(): Promise<KnowledgeDocumentListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: KnowledgeDocument[] }>(
        "/v1/knowledge-base/documents"
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async upload(file: File): Promise<KnowledgeDocumentResponse | ErrorFeeback> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await this.httpClient.post<{ data: KnowledgeDocument }>(
        "/v1/knowledge-base/documents",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      await this.httpClient.delete(`/v1/knowledge-base/documents/${uuid}`);
      return successTask;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listByWorkflow(
    workflowId: string
  ): Promise<KnowledgeDocumentListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: KnowledgeDocument[] }>(
        `/v1/workflows/${workflowId}/knowledge-base/documents`
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async uploadToWorkflow(
    workflowId: string,
    file: File
  ): Promise<KnowledgeDocumentResponse | ErrorFeeback> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await this.httpClient.post<{ data: KnowledgeDocument }>(
        `/v1/workflows/${workflowId}/knowledge-base/documents`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return { data: response.data.data, datetime: new Date().toISOString() };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async deleteFromWorkflow(
    workflowId: string,
    uuid: string
  ): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      await this.httpClient.delete(
        `/v1/workflows/${workflowId}/knowledge-base/documents/${uuid}`
      );
      return successTask;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
