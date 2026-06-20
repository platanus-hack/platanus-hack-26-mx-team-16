import { create } from "zustand";

import type { RunSummary } from "@/src/domain/entities/run-summary";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpRunSummaryRepository } from "@/src/infrastructure/repositories/http-run-summary";

const repository = new HttpRunSummaryRepository(authHttp);

interface RunSummaryState {
  summariesByRun: Record<string, RunSummary>;
  loading: Record<string, boolean>;
  resynthesizing: Record<string, boolean>;
  errors: Record<string, string | null>;

  loadSummary: (runId: string) => Promise<RunSummary | null>;
  resynthesize: (runId: string, force?: boolean) => Promise<RunSummary | null>;
  applyEventUpdate: (runId: string) => Promise<void>;
  reset: () => void;
}

export const useRunSummaryStore = create<RunSummaryState>((set, get) => ({
  summariesByRun: {},
  loading: {},
  resynthesizing: {},
  errors: {},

  loadSummary: async (runId) => {
    set((s) => ({
      loading: { ...s.loading, [runId]: true },
      errors: { ...s.errors, [runId]: null },
    }));
    const response = await repository.getByRunId(runId);
    if ("data" in response) {
      set((s) => ({
        summariesByRun: { ...s.summariesByRun, [runId]: response.data },
        loading: { ...s.loading, [runId]: false },
      }));
      return response.data;
    }
    set((s) => ({
      loading: { ...s.loading, [runId]: false },
      errors: {
        ...s.errors,
        [runId]: "errors" in response ? response.errors[0]?.message ?? "" : "",
      },
    }));
    return null;
  },

  resynthesize: async (runId, force = false) => {
    set((s) => ({
      resynthesizing: { ...s.resynthesizing, [runId]: true },
      errors: { ...s.errors, [runId]: null },
    }));
    const response = await repository.resynthesize(runId, force);
    if ("data" in response) {
      set((s) => ({
        summariesByRun: { ...s.summariesByRun, [runId]: response.data },
        resynthesizing: { ...s.resynthesizing, [runId]: false },
      }));
      return response.data;
    }
    set((s) => ({
      resynthesizing: { ...s.resynthesizing, [runId]: false },
      errors: {
        ...s.errors,
        [runId]: "errors" in response ? response.errors[0]?.message ?? "" : "",
      },
    }));
    return null;
  },

  applyEventUpdate: async (runId) => {
    await get().loadSummary(runId);
  },

  reset: () =>
    set({
      summariesByRun: {},
      loading: {},
      resynthesizing: {},
      errors: {},
    }),
}));
