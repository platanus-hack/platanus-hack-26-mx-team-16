import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpTenantUserRepository } from "@/src/infrastructure/repositories/http-tenant-user";
import { authHttp } from "@/src/infrastructure/http/client";
import type {
  InviteMemberPayload,
  UpdateTenantUserPayload,
} from "@/src/domain/repositories/tenant-user";
import { queryKeys } from "./keys";

const repo = new HttpTenantUserRepository(authHttp);

export function useMembersQuery() {
  return useQuery({
    queryKey: queryKeys.members.all,
    queryFn: async () => {
      const res = await repo.getAll();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useInviteMemberMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: InviteMemberPayload) => {
      const res = await repo.invite(payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.members.all });
      qc.invalidateQueries({ queryKey: queryKeys.invitations.pending });
    },
  });
}

export function usePendingInvitationsQuery() {
  return useQuery({
    queryKey: queryKeys.invitations.pending,
    queryFn: async () => {
      const res = await repo.listPendingInvitations();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
  });
}

export function useSendPasswordResetMutation() {
  return useMutation({
    mutationFn: async (tenantUserId: string) => {
      // Admin path: hits the tenant-scoped endpoint that operates on a
      // known TenantUser, so we get a real 404 if the member is missing
      // (the public /v1/auth/reset-password endpoint is anti-enumeration
      // and silently no-ops for unknown emails, which is misleading for
      // an admin acting on a member they can see).
      const res = await repo.sendPasswordReset(tenantUserId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
  });
}

export function useCancelInvitationMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (invitationId: string) => {
      const res = await repo.cancelInvitation(invitationId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.invitations.pending }),
  });
}

export function useUpdateMemberMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      uuid,
      payload,
    }: {
      uuid: string;
      payload: UpdateTenantUserPayload;
    }) => {
      const res = await repo.update(uuid, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.members.all }),
  });
}

export function useUploadMemberPhotoMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ uuid, file }: { uuid: string; file: File }) => {
      const res = await repo.uploadPhoto(uuid, file);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.members.all }),
  });
}

export function useDeleteMemberMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.members.all }),
  });
}
