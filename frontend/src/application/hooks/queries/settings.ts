import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpTenantSettingsRepository } from "@/src/infrastructure/repositories/tenant-settings";
import { authHttp } from "@/src/infrastructure/http/client";
import { queryKeys } from "./keys";

const repo = new HttpTenantSettingsRepository(authHttp);

export function useSettingsQuery() {
  return useQuery({
    queryKey: queryKeys.settings.all,
    queryFn: async () => {
      const res = await repo.get();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useUpdateSettingsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const res = await repo.update(name);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings.all }),
  });
}

export function useUpdateAvatarMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const res = await repo.updateAvatar(file);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings.all }),
  });
}

export function useRegenerateWebhookKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await repo.regenerateWebhookKey();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings.all }),
  });
}

export function useDeleteTenantMutation() {
  return useMutation({
    mutationFn: async () => {
      const res = await repo.deleteTenant();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
  });
}
