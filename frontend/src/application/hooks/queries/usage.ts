import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpUsageRepository } from "@/src/infrastructure/repositories/http-usage";
import type { ProcessRecordsFilters } from "@/src/domain/repositories/usage";
import { queryKeys } from "./keys";

const repo = new HttpUsageRepository(authHttp);

export function useUsageSummaryQuery() {
  return useQuery({
    queryKey: queryKeys.usage.summary,
    queryFn: async () => {
      const res = await repo.getSummary();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useProcessRecordsInfiniteQuery(
  filters?: Pick<ProcessRecordsFilters, "fromDt" | "toDt">,
) {
  return useInfiniteQuery({
    queryKey: queryKeys.usage.records(filters),
    queryFn: async ({ pageParam }) => {
      const res = await repo.filter({
        ...filters,
        cursor: pageParam as string | undefined,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.pagination?.nextCursor ?? undefined,
  });
}
