import type { CaseNoun } from "@/src/domain/entities/workflow";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  WorkflowListResponse,
  WorkflowResponse,
} from "@/src/domain/responses/workflow";

export interface CreateWorkflowPayload {
  name: string;
  // E7 · F2: el alta elige una PLANTILLA por slug (null/ausente ⇒ extracción
  // estándar). Reemplaza a `workflowType`.
  templateSlug?: string | null;
}

export interface CreateWorkflowFromYamlPayload {
  name: string;
  // Texto YAML crudo de un envelope de bundle (doc-types + pipeline + reglas);
  // el backend lo parsea e importa con overwrite sobre el workflow recién creado.
  yaml: string;
}

export interface UpdateWorkflowPayload {
  name?: string;
  webhookUrl?: string | null;
  webhookEnabled?: boolean;
  webhookEvents?: string[];
  caseNoun?: CaseNoun | null;
}

export interface DeleteResponse {
  status: string;
}

export type WebhookDeliveryStatus =
  | "PENDING"
  | "DELIVERING"
  | "DELIVERED"
  | "FAILED"
  | "SKIPPED";

export interface WebhookEvent {
  uuid: string;
  eventId: string;
  eventType: string;
  workflowId: string;
  processingJobId: string | null;
  documentId: string | null;
  destinationId: string | null;
  documentStatus: string;
  deliveryStatus: WebhookDeliveryStatus;
  attempts: number;
  responseStatus: number | null;
  lastError: string | null;
  lastAttemptAt: string | null;
  deliveredAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface WebhookSecret {
  webhookSecret: string;
}

export interface WebhookEventsResponse {
  data: WebhookEvent[];
}

export interface WebhookEventResponse {
  data: WebhookEvent;
}

export interface WebhookSecretResponse {
  data: WebhookSecret;
}

export interface WorkflowRepository {
  getAll(): Promise<WorkflowListResponse | ErrorFeeback>;
  getById(uuid: string): Promise<WorkflowResponse | ErrorFeeback>;
  create(
    payload: CreateWorkflowPayload
  ): Promise<WorkflowResponse | ErrorFeeback>;
  createFromYaml(
    payload: CreateWorkflowFromYamlPayload
  ): Promise<WorkflowResponse | ErrorFeeback>;
  update(
    uuid: string,
    payload: UpdateWorkflowPayload
  ): Promise<WorkflowResponse | ErrorFeeback>;
  delete(uuid: string): Promise<DeleteResponse | ErrorFeeback>;
  regenerateWebhookSecret(
    uuid: string
  ): Promise<WebhookSecretResponse | ErrorFeeback>;
  listWebhookEvents(
    uuid: string,
    deliveryStatus?: string
  ): Promise<WebhookEventsResponse | ErrorFeeback>;
  replayWebhookEvent(
    uuid: string,
    eventId: string
  ): Promise<WebhookEventResponse | ErrorFeeback>;
}
