import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MockBillingRepository } from "@/src/infrastructure/repositories/mock-billing";
import { queryKeys } from "./keys";

const repo = new MockBillingRepository();

export function useBillingQuery() {
  return useQuery({
    queryKey: queryKeys.billing.all,
    queryFn: async () => {
      const res = await repo.getBillingData();
      if ("errors" in res) throw new Error(res.errors?.[0]?.message);
      return res;
    },
  });
}

export function useBuyCreditsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (amount: number) => {
      const res = await repo.buyCredits(amount);
      if ("errors" in res) throw new Error(res.errors?.[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.billing.all }),
  });
}
