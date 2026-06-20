import { useQuery } from "@tanstack/react-query";

import type { OverviewData } from "@/src/domain/entities/dashboard/overview";
import type { ProcessingData } from "@/src/domain/entities/dashboard/processing";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpDashboardRepository } from "@/src/infrastructure/repositories/http-dashboard";
import { queryKeys } from "./keys";

const repo = new HttpDashboardRepository(authHttp);

export interface UseDashboardOverviewOptions {
  throughputMonths?: number;
  recentLimit?: number;
}

export interface UseDashboardProcessingOptions {
  liveLimit?: number;
}

/**
 * Loads the Overview tab payload (summary + throughput + recent docs).
 *
 * `staleTime` is the only thing keeping data fresh — refetches normally
 * happen on-demand via `queryClient.invalidateQueries(["dashboard",
 * "overview"])` triggered by `useDashboardEvents`. The 30s `staleTime`
 * is the fallback for the case where SSE is disconnected.
 */
export function useDashboardOverview(
  options: UseDashboardOverviewOptions = {}
) {
  const params = {
    throughputMonths: options.throughputMonths ?? 12,
    recentLimit: options.recentLimit ?? 5,
  };

  return useQuery<OverviewData>({
    queryKey: queryKeys.dashboard.overview(params),
    queryFn: async () => {
      const res = await repo.getOverview(params);
      if (isErrorFeedback(res)) {
        throw new Error(res.errors[0]?.message ?? "Dashboard overview failed");
      }
      return res.data;
    },
    staleTime: 30_000,
  });
}

/**
 * Loads the Processing tab payload (summary + stages + live processing).
 *
 * Shorter `staleTime` than Overview because the data is more time-sensitive
 * — if SSE is down, users still get acceptably-fresh numbers on interaction.
 */
export function useDashboardProcessing(
  options: UseDashboardProcessingOptions = {}
) {
  const params = { liveLimit: options.liveLimit ?? 5 };

  return useQuery<ProcessingData>({
    queryKey: queryKeys.dashboard.processing(params),
    queryFn: async () => {
      const res = await repo.getProcessing(params);
      if (isErrorFeedback(res)) {
        throw new Error(
          res.errors[0]?.message ?? "Dashboard processing failed"
        );
      }
      return res.data;
    },
    staleTime: 10_000,
  });
}
