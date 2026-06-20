import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CreateWorkflowFromYamlPayload,
  CreateWorkflowPayload,
  UpdateWorkflowPayload,
} from "@/src/domain/repositories/workflow";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowRepository } from "@/src/infrastructure/repositories/http-workflow";
import { queryKeys } from "./keys";

const repo = new HttpWorkflowRepository(authHttp);

export function useWorkflowsQuery() {
  return useQuery({
    queryKey: queryKeys.workflows.all,
    queryFn: async () => {
      const res = await repo.getAll();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useWorkflowQuery(uuid: string) {
  return useQuery({
    queryKey: queryKeys.workflows.detail(uuid),
    queryFn: async () => {
      const res = await repo.getById(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!uuid,
  });
}

export function useCreateWorkflowMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateWorkflowPayload) => {
      const res = await repo.create(payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all }),
  });
}

export function useCreateWorkflowFromYamlMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateWorkflowFromYamlPayload) => {
      const res = await repo.createFromYaml(payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all }),
  });
}

/**
 * Duplica un workflow (deep copy: doctypes, reglas y pipeline) vía
 * POST /v1/workflows/{uuid}/duplicate. Devuelve el workflow creado (201).
 * ADR 0002: el pipeline es propiedad del workflow, por lo que se copia con él.
 */
export function useDuplicateWorkflowMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ uuid, name }: { uuid: string; name: string }) => {
      const res = await authHttp.post(`/v1/workflows/${uuid}/duplicate`, {
        name,
      });
      const body = res.data as { data: { uuid: string } };
      return body.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all }),
  });
}

export function useUpdateWorkflowMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      uuid,
      payload,
    }: {
      uuid: string;
      payload: UpdateWorkflowPayload;
    }) => {
      const res = await repo.update(uuid, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all });
      qc.invalidateQueries({ queryKey: queryKeys.workflows.detail(data.uuid) });
    },
  });
}

export function useDeleteWorkflowMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all }),
  });
}

export function useWorkflowEventsQuery(uuid: string, deliveryStatus?: string) {
  return useQuery({
    queryKey: queryKeys.workflows.events(uuid, deliveryStatus),
    queryFn: async () => {
      const res = await repo.listWebhookEvents(uuid, deliveryStatus);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!uuid,
  });
}

export function useRegenerateWebhookSecretMutation() {
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.regenerateWebhookSecret(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useReplayWebhookEventMutation(uuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: string) => {
      const res = await repo.replayWebhookEvent(uuid, eventId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    // Prefix match invalidates every deliveryStatus filter variant.
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["workflows", uuid, "events"] }),
  });
}
