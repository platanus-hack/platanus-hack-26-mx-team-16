import { useQuery } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";
import type { WorkflowPhaseExecution } from "@/src/domain/entities/workflow-phase-execution";

import { queryKeys } from "./keys";

interface Envelope<T> {
  data: T;
}

/**
 * Per-phase execution timeline of one processing job (an "Ejecución").
 * `refetchInterval` lets the detail poll while the run is still in flight so the
 * Step-Functions view advances live.
 */
export function usePhaseExecutionsQuery(
  workflowId: string,
  processingJobId: string | null,
  options: { enabled?: boolean; refetchInterval?: number | false } = {}
) {
  return useQuery({
    queryKey: queryKeys.processingJobs.phases(workflowId, processingJobId ?? ""),
    queryFn: async () => {
      const res = await authHttp.get<Envelope<WorkflowPhaseExecution[]>>(
        `/v1/workflows/${workflowId}/jobs/${processingJobId}/phases`
      );
      return res.data.data;
    },
    enabled:
      (options.enabled ?? true) && !!workflowId && Boolean(processingJobId),
    refetchInterval: options.refetchInterval ?? false,
  });
}
