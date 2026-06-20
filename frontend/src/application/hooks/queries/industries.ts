import { useQuery } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";
import { HttpIndustryRepository } from "@/src/infrastructure/repositories/http-industry";
import { queryKeys } from "./keys";

const repo = new HttpIndustryRepository(authHttp);

export function useIndustriesQuery() {
  return useQuery({
    queryKey: queryKeys.industries.all,
    queryFn: async () => {
      const res = await repo.list();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    staleTime: 5 * 60 * 1000,
  });
}
