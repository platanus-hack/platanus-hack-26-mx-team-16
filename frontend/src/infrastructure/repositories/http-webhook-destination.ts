import type { AxiosError, AxiosInstance } from "axios";

import type {
  CreateWebhookDestinationPayload,
  UpdateWebhookDestinationPayload,
  WebhookDestination,
  WebhookDestinationWithSecret,
} from "@/src/domain/entities/webhook-destination";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { WebhookEvent } from "@/src/domain/repositories/workflow";
import { authHttp } from "@/src/infrastructure/http/client";
import { handleHttpError } from "@/src/utils/http-error-handler";

/**
 * Per-workflow webhook destinations. Goes through the middleware proxy
 * (`/api/v1/*` → backend with `X-Api-Key`) via `authHttp`. The route param
 * `wfSlug` carries the workflow uuid used by the API.
 */
export class HttpWebhookDestinationRepository {
  private httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance = authHttp) {
    this.httpClient = httpClient;
  }

  private base(workflowId: string): string {
    return `/v1/workflows/${workflowId}/webhook-destinations`;
  }

  async list(
    workflowId: string
  ): Promise<{ data: WebhookDestination[] } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{
        data: WebhookDestination[];
      }>(this.base(workflowId));
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async get(
    workflowId: string,
    destinationId: string
  ): Promise<{ data: WebhookDestination } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WebhookDestination }>(
        `${this.base(workflowId)}/${destinationId}`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    workflowId: string,
    payload: CreateWebhookDestinationPayload
  ): Promise<{ data: WebhookDestination } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WebhookDestination }>(
        this.base(workflowId),
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    workflowId: string,
    destinationId: string,
    payload: UpdateWebhookDestinationPayload
  ): Promise<{ data: WebhookDestination } | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: WebhookDestination }>(
        `${this.base(workflowId)}/${destinationId}`,
        payload
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async remove(
    workflowId: string,
    destinationId: string
  ): Promise<{ deleted: boolean } | ErrorFeeback> {
    try {
      await this.httpClient.delete(`${this.base(workflowId)}/${destinationId}`);
      return { deleted: true };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async revealSecret(
    workflowId: string,
    destinationId: string
  ): Promise<{ data: WebhookDestinationWithSecret } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{
        data: WebhookDestinationWithSecret;
      }>(`${this.base(workflowId)}/${destinationId}/secret`);
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async regenerateSecret(
    workflowId: string,
    destinationId: string
  ): Promise<{ data: WebhookDestinationWithSecret } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{
        data: WebhookDestinationWithSecret;
      }>(`${this.base(workflowId)}/${destinationId}/secret`);
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listEvents(
    workflowId: string,
    destinationId: string,
    deliveryStatus?: string
  ): Promise<{ data: WebhookEvent[] } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WebhookEvent[] }>(
        `${this.base(workflowId)}/${destinationId}/events`,
        { params: deliveryStatus ? { deliveryStatus } : undefined }
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  /** Replay reuses the workflow-level event replay route (destination-aware). */
  async replayEvent(
    workflowId: string,
    eventId: string
  ): Promise<{ data: WebhookEvent } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WebhookEvent }>(
        `/v1/workflows/${workflowId}/events/${eventId}/replay`
      );
      return { data: response.data.data };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
