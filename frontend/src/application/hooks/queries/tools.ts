import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";

export interface Tool {
  uuid: string;
  name: string;
  displayName: string;
  description: string | null;
  transport: string;
  connectionAccountId: string | null;
  enabled: boolean;
  createdAt: string | null;
}

export interface ConnectionAccount {
  uuid: string;
  displayName: string;
  provider: string;
}

export type ToolTransport = "HTTP" | "PYTHON" | "JS";

export interface CreateToolInput {
  name: string;
  displayName: string;
  description?: string;
  transport: ToolTransport;
  // HTTP transport: cuenta de conexión (LOOKUP) + endpoint.
  connectionAccountId?: string;
  baseUrl?: string;
  path?: string;
  // Script transport (PYTHON/JS): el código corre en el sandbox aislado; no
  // usa cuenta de conexión.
  runtime?: string;
  entrypoint?: string;
  code?: string;
}

const DEFAULT_RUNTIME: Record<ToolTransport, string> = {
  HTTP: "",
  PYTHON: "python3.12",
  JS: "node20",
};

type Envelope<T> = { data: T } | { errors: { message: string }[] };

// Re-scope 2026-06: las tools son 1:1 del workflow (como el pipeline); la
// cuenta de conexión (secreto) sigue siendo org-level.
const base = (workflowId: string) => `/v1/workflows/${workflowId}/tools`;
const CONNECTIONS = "/v1/connections";

const api = {
  list: async (workflowId: string): Promise<Envelope<Tool[]>> =>
    (await authHttp.get(base(workflowId))).data,
  connections: async (): Promise<Envelope<ConnectionAccount[]>> =>
    (await authHttp.get(CONNECTIONS)).data,
  create: async (
    workflowId: string,
    input: CreateToolInput
  ): Promise<Envelope<Tool>> => {
    const isScript = input.transport === "PYTHON" || input.transport === "JS";
    const config = isScript
      ? {
          runtime: input.runtime || DEFAULT_RUNTIME[input.transport],
          entrypoint: input.entrypoint || "main",
          code: input.code ?? "",
        }
      : {
          base_url: input.baseUrl,
          path: input.path,
          method: "POST",
          auth: "bearer",
          host_allowlist: [],
        };
    const body: Record<string, unknown> = {
      name: input.name,
      display_name: input.displayName,
      description: input.description,
      transport: input.transport,
      input_schema: {},
      output_schema: {},
      config,
    };
    // Las script tools no llevan cuenta de conexión (el backend la deja NULL).
    if (!isScript) body.connection_account_id = input.connectionAccountId;
    return (await authHttp.post(base(workflowId), body)).data;
  },
  remove: async (
    workflowId: string,
    id: string
  ): Promise<Envelope<{ deleted: boolean }>> =>
    (await authHttp.delete(`${base(workflowId)}/${id}`)).data,
};

const toolsKey = (workflowId: string) => ["tools", workflowId] as const;
const CONNECTIONS_KEY = ["connection-accounts"] as const;

export function useToolsQuery(workflowId: string) {
  return useQuery({
    queryKey: toolsKey(workflowId),
    enabled: Boolean(workflowId),
    queryFn: async () => {
      const res = await api.list(workflowId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useConnectionAccountsQuery() {
  return useQuery({
    queryKey: CONNECTIONS_KEY,
    queryFn: async () => {
      const res = await api.connections();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useCreateToolMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateToolInput) => {
      const res = await api.create(workflowId, input);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: toolsKey(workflowId) }),
  });
}

export function useDeleteToolMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.remove(workflowId, id);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: toolsKey(workflowId) }),
  });
}
