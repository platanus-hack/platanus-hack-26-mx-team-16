import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";

export interface TenantApiKey {
  uuid: string;
  name: string;
  prefix: string;
  enabled: boolean;
  lastUsedAt: string | null;
  createdAt: string | null;
}

// Returned only by the mint endpoint — the cleartext key, shown once.
export interface MintedApiKey extends TenantApiKey {
  key: string;
}

type Envelope<T> = { data: T } | { errors: { message: string }[] };

const BASE = "/v1/tenants/api-keys";

const api = {
  list: async (): Promise<Envelope<TenantApiKey[]>> =>
    (await authHttp.get(BASE)).data,
  create: async (name: string): Promise<Envelope<MintedApiKey>> =>
    (await authHttp.post(BASE, { name })).data,
  revoke: async (id: string): Promise<Envelope<{ revoked: boolean }>> =>
    (await authHttp.delete(`${BASE}/${id}`)).data,
};

const KEY = ["tenant-api-keys"] as const;

export function useApiKeysQuery() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const res = await api.list();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useMintApiKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const res = await api.create(name);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRevokeApiKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.revoke(id);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
