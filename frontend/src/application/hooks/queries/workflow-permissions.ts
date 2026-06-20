import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  WorkflowAccessType,
  WorkflowMemberRole,
} from "@/src/domain/entities/workflow-permission";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowPermissionRepository } from "@/src/infrastructure/repositories/http-workflow-permission";
import { queryKeys } from "./keys";

const repo = new HttpWorkflowPermissionRepository(authHttp);

export function useWorkflowPermissionsQuery(workflowUuid: string) {
  return useQuery({
    queryKey: queryKeys.permissions.all(workflowUuid),
    queryFn: async () => {
      const res = await repo.getPermissions(workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowUuid,
  });
}

export function useAssignableUsersQuery(workflowUuid: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.permissions.assignableUsers(workflowUuid),
    queryFn: async () => {
      const res = await repo.listAssignableUsers(workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowUuid && enabled,
  });
}

export function useUpdateAccessTypeMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (accessType: WorkflowAccessType) => {
      const res = await repo.updateAccessType(workflowUuid, accessType);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.permissions.all(workflowUuid), data);
      // Private workflows drop off non-members' workflow lists.
      qc.invalidateQueries({ queryKey: queryKeys.workflows.all });
    },
  });
}

export function useAddMemberMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      role,
    }: {
      userId: string;
      role: WorkflowMemberRole;
    }) => {
      const res = await repo.addMember(workflowUuid, userId, role);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.permissions.all(workflowUuid) });
      qc.invalidateQueries({
        queryKey: queryKeys.permissions.assignableUsers(workflowUuid),
      });
    },
  });
}

export function useUpdateMemberRoleMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      role,
    }: {
      userId: string;
      role: WorkflowMemberRole;
    }) => {
      const res = await repo.updateMemberRole(workflowUuid, userId, role);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.permissions.all(workflowUuid) }),
  });
}

export function useRemoveMemberMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const res = await repo.removeMember(workflowUuid, userId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.permissions.all(workflowUuid) });
      qc.invalidateQueries({
        queryKey: queryKeys.permissions.assignableUsers(workflowUuid),
      });
    },
  });
}
