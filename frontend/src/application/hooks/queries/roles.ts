import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpTenantRoleRepository } from "@/src/infrastructure/repositories/http-tenant-role";
import { authHttp } from "@/src/infrastructure/http/client";
import type {
  CreateTenantRolePayload,
  UpdateTenantRolePayload,
} from "@/src/domain/repositories/tenant-role";
import { queryKeys } from "./keys";

const repo = new HttpTenantRoleRepository(authHttp);

export function useRolesQuery() {
  return useQuery({
    queryKey: queryKeys.roles.all,
    queryFn: async () => {
      const res = await repo.getAll();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useCreateRoleMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateTenantRolePayload) => {
      const res = await repo.create(payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.roles.all }),
  });
}

export function useUpdateRoleMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      uuid,
      payload,
    }: {
      uuid: string;
      payload: UpdateTenantRolePayload;
    }) => {
      const res = await repo.update(uuid, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.roles.all }),
  });
}

export function useDeleteRoleMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.roles.all }),
  });
}
