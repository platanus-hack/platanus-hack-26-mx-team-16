import type { AxiosError, AxiosInstance } from "axios";
import type { Workflow } from "@/src/domain/entities/workflow";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CreateWorkflowFromYamlPayload,
  CreateWorkflowPayload,
  DeleteResponse,
  UpdateWorkflowPayload,
  WebhookEvent,
  WebhookEventResponse,
  WebhookEventsResponse,
  WebhookSecret,
  WebhookSecretResponse,
  WorkflowRepository,
} from "@/src/domain/repositories/workflow";
import type {
  WorkflowListResponse,
  WorkflowResponse,
} from "@/src/domain/responses/workflow";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpWorkflowRepository implements WorkflowRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async getAll(): Promise<WorkflowListResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: Workflow[] }>(
        "/v1/workflows"
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getById(uuid: string): Promise<WorkflowResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: Workflow }>(
        `/v1/workflows/${uuid}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    payload: CreateWorkflowPayload
  ): Promise<WorkflowResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: Workflow }>(
        "/v1/workflows",
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async createFromYaml(
    payload: CreateWorkflowFromYamlPayload
  ): Promise<WorkflowResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: Workflow }>(
        "/v1/workflows/import-yaml",
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    uuid: string,
    payload: UpdateWorkflowPayload
  ): Promise<WorkflowResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: Workflow }>(
        `/v1/workflows/${uuid}`,
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(uuid: string): Promise<DeleteResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.delete<{ data: DeleteResponse }>(
        `/v1/workflows/${uuid}`
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async regenerateWebhookSecret(
    uuid: string
  ): Promise<WebhookSecretResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WebhookSecret }>(
        `/v1/workflows/${uuid}/webhook-secret`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listWebhookEvents(
    uuid: string,
    deliveryStatus?: string
  ): Promise<WebhookEventsResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WebhookEvent[] }>(
        `/v1/workflows/${uuid}/events`,
        { params: deliveryStatus ? { deliveryStatus } : undefined }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async replayWebhookEvent(
    uuid: string,
    eventId: string
  ): Promise<WebhookEventResponse | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WebhookEvent }>(
        `/v1/workflows/${uuid}/events/${eventId}/replay`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
