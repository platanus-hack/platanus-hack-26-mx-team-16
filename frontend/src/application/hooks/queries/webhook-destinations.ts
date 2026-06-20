import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  CreateWebhookDestinationPayload,
  UpdateWebhookDestinationPayload,
} from "@/src/domain/entities/webhook-destination";
import { HttpWebhookDestinationRepository } from "@/src/infrastructure/repositories/http-webhook-destination";
import { queryKeys } from "./keys";

const repo = new HttpWebhookDestinationRepository();

export function useWebhookDestinationsQuery(workflowId: string) {
  return useQuery({
    queryKey: queryKeys.webhookDestinations.all(workflowId),
    queryFn: async () => {
      const res = await repo.list(workflowId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowId,
  });
}

export function useWebhookDestinationQuery(
  workflowId: string,
  destinationId: string
) {
  return useQuery({
    queryKey: queryKeys.webhookDestinations.detail(workflowId, destinationId),
    queryFn: async () => {
      const res = await repo.get(workflowId, destinationId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowId && !!destinationId,
  });
}

export function useCreateWebhookDestinationMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateWebhookDestinationPayload) => {
      const res = await repo.create(workflowId, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.webhookDestinations.all(workflowId),
      }),
  });
}

export function useUpdateWebhookDestinationMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      destinationId,
      payload,
    }: {
      destinationId: string;
      payload: UpdateWebhookDestinationPayload;
    }) => {
      const res = await repo.update(workflowId, destinationId, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: queryKeys.webhookDestinations.all(workflowId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.webhookDestinations.detail(workflowId, data.uuid),
      });
    },
  });
}

export function useDeleteWebhookDestinationMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (destinationId: string) => {
      const res = await repo.remove(workflowId, destinationId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.webhookDestinations.all(workflowId),
      }),
  });
}

export function useRegenerateWebhookDestinationSecretMutation(
  workflowId: string
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (destinationId: string) => {
      const res = await repo.regenerateSecret(workflowId, destinationId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (data) =>
      qc.invalidateQueries({
        queryKey: queryKeys.webhookDestinations.detail(workflowId, data.uuid),
      }),
  });
}

/**
 * Fetches the stored signing secret on demand (Stripe-style reveal). Read-only,
 * so it invalidates nothing; the detail UI holds the returned secret in local
 * state while the user views/copies it.
 */
export function useRevealWebhookDestinationSecretMutation(workflowId: string) {
  return useMutation({
    mutationFn: async (destinationId: string) => {
      const res = await repo.revealSecret(workflowId, destinationId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useWebhookDestinationEventsQuery(
  workflowId: string,
  destinationId: string,
  deliveryStatus?: string
) {
  return useQuery({
    queryKey: queryKeys.webhookDestinations.events(
      workflowId,
      destinationId,
      deliveryStatus
    ),
    queryFn: async () => {
      const res = await repo.listEvents(workflowId, destinationId, deliveryStatus);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowId && !!destinationId,
  });
}

export function useReplayWebhookDestinationEventMutation(
  workflowId: string,
  destinationId: string
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: string) => {
      const res = await repo.replayEvent(workflowId, eventId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    // Prefix match invalidates every deliveryStatus filter variant.
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: [
          "webhook-destinations",
          workflowId,
          destinationId,
          "events",
        ],
      }),
  });
}
