import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpCaseRepository } from "@/src/infrastructure/repositories/http-case";
import { authHttp } from "@/src/infrastructure/http/client";
import { queryKeys } from "@/src/application/hooks/queries/keys";
import type { WorkflowCaseFilters } from "@/src/domain/entities/case";

const repo = new HttpCaseRepository(authHttp);

export function useCasesQuery(workflowUuid: string) {
  return useQuery({
    queryKey: queryKeys.cases.all(workflowUuid),
    queryFn: async () => {
      const res = await repo.getAll(workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowUuid,
  });
}

export function useCasesInfiniteQuery(
  workflowUuid: string,
  filters?: Omit<WorkflowCaseFilters, "cursor">
) {
  return useInfiniteQuery({
    queryKey: queryKeys.cases.paginated(workflowUuid, filters),
    queryFn: async ({ pageParam }) => {
      const res = await repo.getPaginated(workflowUuid, {
        ...filters,
        cursor: pageParam as string | undefined,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.pagination?.nextCursor ?? undefined,
    enabled: !!workflowUuid,
  });
}

export function useCaseDetailQuery(workflowUuid: string, caseUuid: string) {
  return useQuery({
    queryKey: queryKeys.cases.detail(workflowUuid, caseUuid),
    queryFn: async () => {
      const res = await repo.getById(workflowUuid, caseUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowUuid && !!caseUuid,
  });
}

export function useCreateCaseMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const res = await repo.create(workflowUuid, { name });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.cases.all(workflowUuid) });
      qc.invalidateQueries({ queryKey: queryKeys.cases.paginated(workflowUuid) });
    },
  });
}

export function useDeleteCaseMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (caseUuid: string) => {
      const res = await repo.delete(workflowUuid, caseUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.cases.all(workflowUuid) });
      qc.invalidateQueries({ queryKey: queryKeys.cases.paginated(workflowUuid) });
    },
  });
}
