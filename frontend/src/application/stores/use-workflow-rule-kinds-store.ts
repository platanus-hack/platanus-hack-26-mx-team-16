"use client";

import { create } from "zustand";
import type { WorkflowRuleKindDescriptor } from "@/src/domain/entities/workflow-rule-kind";
import { isErrorFeedback, showErrorItems } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowRuleRepository } from "@/src/infrastructure/repositories/http-workflow-rule";

interface WorkflowRuleKindsState {
  kinds: WorkflowRuleKindDescriptor[];
  byName: Record<string, WorkflowRuleKindDescriptor>;
  isLoading: boolean;
  error: string | null;
  hasHydrated: boolean;
  hydrate: () => Promise<void>;
}

const repository = new HttpWorkflowRuleRepository(authHttp);

export const useWorkflowRuleKindsStore = create<WorkflowRuleKindsState>((set, get) => ({
  kinds: [],
  byName: {},
  isLoading: false,
  error: null,
  hasHydrated: false,
  hydrate: async () => {
    if (get().hasHydrated || get().isLoading) return;
    set({ isLoading: true, error: null });
    const result = await repository.listKinds();
    if (!isErrorFeedback(result) && "data" in result) {
      const byName: Record<string, WorkflowRuleKindDescriptor> = {};
      for (const kind of result.data) byName[kind.name] = kind;
      set({
        kinds: result.data,
        byName,
        isLoading: false,
        hasHydrated: true,
        error: null,
      });
      return;
    }
    set({
      isLoading: false,
      hasHydrated: true,
      error: isErrorFeedback(result) ? showErrorItems(result.errors) : "Unknown error",
    });
  },
}));
