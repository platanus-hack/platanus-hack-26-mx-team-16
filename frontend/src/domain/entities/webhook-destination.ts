/**
 * Per-workflow webhook destination (mirrors backend workflows module §4.3).
 * A workflow may have many destinations; each owns its URL, signing secret and
 * the event types it is subscribed to. Deliveries are recorded as WebhookEvents
 * tagged with the destination id (delivery log + charts).
 */

export type WebhookDestinationStatus = "ACTIVE" | "DISABLED";

export interface WebhookDestination {
  uuid: string;
  tenantId: string;
  workflowId: string;
  name: string;
  url: string;
  description: string | null;
  enabled: boolean;
  status: WebhookDestinationStatus;
  subscribedEvents: string[];
  apiVersion: string | null;
  hasSecret: boolean;
  createdAt: string | null;
  updatedAt: string | null;
}

/** Returned once by the regenerate-secret endpoint so the UI can reveal it. */
export interface WebhookDestinationWithSecret extends WebhookDestination {
  secret: string;
}

export interface CreateWebhookDestinationPayload {
  name: string;
  url: string;
  description?: string | null;
  enabled?: boolean;
  subscribedEvents?: string[];
  secret?: string | null;
  apiVersion?: string | null;
}

export interface UpdateWebhookDestinationPayload {
  name?: string;
  url?: string;
  description?: string | null;
  enabled?: boolean;
  subscribedEvents?: string[];
  secret?: string | null;
  apiVersion?: string | null;
}

/** Outbound event types a destination can subscribe to (spec §4.1.1). */
export const WEBHOOK_EVENT_TYPES = [
  "document.extracted",
  "document.failed",
] as const;
