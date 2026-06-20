import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as React from "react";

import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowProcessingJobRepository } from "@/src/infrastructure/repositories/http-workflow-processing-job";
import { queryKeys } from "./keys";
import type { ProcessingJobFilters } from "@/src/domain/entities/workflow-processing-job";

const repo = new HttpWorkflowProcessingJobRepository(authHttp);

export function useWorkflowProcessingJobsQuery(
  workflowUuid: string,
  options: { workflowCaseId?: string; enabled?: boolean } = {}
) {
  return useQuery({
    queryKey: queryKeys.processingJobs.all(workflowUuid),
    queryFn: async () => {
      const res = await repo.list({
        workflowId: workflowUuid,
        workflowCaseId: options.workflowCaseId,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: options.enabled !== false && !!workflowUuid,
  });
}

export function useWorkflowProcessingJobsInfiniteQuery(
  workflowUuid: string,
  filters?: Omit<ProcessingJobFilters, "cursor">,
  options: { enabled?: boolean } = {}
) {
  return useInfiniteQuery({
    queryKey: queryKeys.processingJobs.paginated(workflowUuid, filters),
    queryFn: async ({ pageParam }) => {
      const res = await repo.listPaginated(workflowUuid, {
        ...filters,
        cursor: pageParam as string | undefined,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.pagination?.nextCursor ?? undefined,
    enabled: options.enabled !== false && !!workflowUuid,
  });
}

export function useDeleteWorkflowProcessingJobMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (processingJobId: string) => {
      const res = await repo.delete({
        workflowId: workflowUuid,
        processingJobId,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.processingJobs.all(workflowUuid),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.processingJobs.paginated(workflowUuid),
      });
    },
  });
}
