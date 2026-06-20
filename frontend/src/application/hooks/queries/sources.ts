import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";

export type SourceAuthMode = "api_key" | "hmac";

export interface IngestSource {
  uuid: string;
  workflowId: string;
  provider: string;
  routeToken: string;
  authMode: SourceAuthMode;
  enabled: boolean;
  ingestUrl: string;
  hasSecret: boolean;
  createdAt: string | null;
}

// Returned only by the create endpoint — the secret credential, shown once.
export interface CreatedIngestSource extends IngestSource {
  apiKey?: string;
  signingSecret?: string;
}

export type SourceEventStatus =
  | "PENDING"
  | "RUNNING"
  | "PROCESSING"
  | "COMPLETED"
  | "PARTIAL"
  | "FAILED";

// One inbound ingest request: a file the source received and its processing
// outcome (the "response"). Backed by a WorkflowProcessingJob server-side.
export interface SourceEvent {
  uuid: string;
  fileName: string | null;
  status: SourceEventStatus;
  caseId: string | null;
  error: string | null;
  createdAt: string | null;
}

export interface SourceWorkflow {
  uuid: string;
  name: string;
  slug: string;
}

export interface CreateSourceInput {
  workflowId: string;
  authMode: SourceAuthMode;
}

export interface UpdateSourceInput {
  workflowId: string; // for cache invalidation
  sourceId: string;
  enabled?: boolean;
  authMode?: SourceAuthMode;
}

export interface DeleteSourceInput {
  workflowId: string; // for cache invalidation
  sourceId: string;
}

type Envelope<T> = { data: T } | { errors: { message: string }[] };

const BASE = "/v1/connections/sources";

const api = {
  workflows: async (): Promise<Envelope<SourceWorkflow[]>> =>
    (await authHttp.get("/v1/workflows")).data,
  list: async (workflowId: string): Promise<Envelope<IngestSource[]>> =>
    (await authHttp.get(BASE, { params: { workflow_id: workflowId } })).data,
  create: async (
    input: CreateSourceInput
  ): Promise<Envelope<CreatedIngestSource>> =>
    (
      await authHttp.post(BASE, {
        workflow_id: input.workflowId,
        auth_mode: input.authMode,
        config: {},
      })
    ).data,
  update: async (
    input: UpdateSourceInput
  ): Promise<Envelope<CreatedIngestSource>> => {
    const body: Record<string, unknown> = {};
    if (input.enabled !== undefined) body.enabled = input.enabled;
    if (input.authMode !== undefined) body.auth_mode = input.authMode;
    return (await authHttp.patch(`${BASE}/${input.sourceId}`, body)).data;
  },
  remove: async (sourceId: string): Promise<Envelope<{ deleted: boolean }>> =>
    (await authHttp.delete(`${BASE}/${sourceId}`)).data,
  events: async (sourceId: string): Promise<Envelope<SourceEvent[]>> =>
    (await authHttp.get(`${BASE}/${sourceId}/events`)).data,
};

const WORKFLOWS_KEY = ["sources-workflows"] as const;
const sourcesKey = (workflowId: string) =>
  ["ingest-sources", workflowId] as const;
const sourceEventsKey = (sourceId: string) =>
  ["ingest-source-events", sourceId] as const;

export function useWorkflowsForSourcesQuery() {
  return useQuery({
    queryKey: WORKFLOWS_KEY,
    queryFn: async () => {
      const res = await api.workflows();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useSourcesQuery(workflowId: string | null) {
  return useQuery({
    queryKey: sourcesKey(workflowId ?? ""),
    enabled: !!workflowId,
    queryFn: async () => {
      const res = await api.list(workflowId as string);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useSourceEventsQuery(sourceId: string | null) {
  return useQuery({
    queryKey: sourceEventsKey(sourceId ?? ""),
    enabled: !!sourceId,
    queryFn: async () => {
      const res = await api.events(sourceId as string);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useCreateSourceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateSourceInput) => {
      const res = await api.create(input);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (_data, input) =>
      qc.invalidateQueries({ queryKey: sourcesKey(input.workflowId) }),
  });
}

export function useUpdateSourceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateSourceInput) => {
      const res = await api.update(input);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (_data, input) =>
      qc.invalidateQueries({ queryKey: sourcesKey(input.workflowId) }),
  });
}

export function useDeleteSourceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: DeleteSourceInput) => {
      const res = await api.remove(input.sourceId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (_data, input) =>
      qc.invalidateQueries({ queryKey: sourcesKey(input.workflowId) }),
  });
}
