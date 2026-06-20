import { create } from "zustand";

import type { WorkflowSynthesisConfig } from "@/src/domain/entities/run-summary";
import { authHttp } from "@/src/infrastructure/http/client";
import type { UpdateSynthesisConfigPayload } from "@/src/domain/repositories/run-summary";
import { HttpRunSummaryRepository } from "@/src/infrastructure/repositories/http-run-summary";

const repository = new HttpRunSummaryRepository(authHttp);

interface State {
  configByWorkflow: Record<string, WorkflowSynthesisConfig>;
  loading: Record<string, boolean>;
  saving: Record<string, boolean>;
  errors: Record<string, string | null>;

  loadConfig: (workflowId: string) => Promise<WorkflowSynthesisConfig | null>;
  updateConfig: (
    workflowId: string,
    payload: UpdateSynthesisConfigPayload
  ) => Promise<WorkflowSynthesisConfig | null>;
  clearError: (workflowId: string) => void;
  reset: () => void;
}

export const useWorkflowSynthesisConfigStore = create<State>((set) => ({
  configByWorkflow: {},
  loading: {},
  saving: {},
  errors: {},

  loadConfig: async (workflowId) => {
    set((s) => ({
      loading: { ...s.loading, [workflowId]: true },
      errors: { ...s.errors, [workflowId]: null },
    }));
    const response = await repository.getWorkflowConfig(workflowId);
    if ("data" in response) {
      set((s) => ({
        configByWorkflow: { ...s.configByWorkflow, [workflowId]: response.data },
        loading: { ...s.loading, [workflowId]: false },
      }));
      return response.data;
    }
    set((s) => ({
      loading: { ...s.loading, [workflowId]: false },
      errors: {
        ...s.errors,
        [workflowId]:
          "errors" in response
            ? response.errors[0]?.message ?? "No pudimos cargar la configuración."
            : "No pudimos cargar la configuración.",
      },
    }));
    return null;
  },

  updateConfig: async (workflowId, payload) => {
    set((s) => ({
      saving: { ...s.saving, [workflowId]: true },
      errors: { ...s.errors, [workflowId]: null },
    }));
    const response = await repository.updateWorkflowConfig(workflowId, payload);
    if ("data" in response) {
      set((s) => ({
        configByWorkflow: { ...s.configByWorkflow, [workflowId]: response.data },
        saving: { ...s.saving, [workflowId]: false },
      }));
      return response.data;
    }
    const message =
      "errors" in response
        ? response.errors[0]?.message ?? "No pudimos guardar la configuración."
        : "No pudimos guardar la configuración.";
    set((s) => ({
      saving: { ...s.saving, [workflowId]: false },
      errors: { ...s.errors, [workflowId]: message },
    }));
    return null;
  },

  clearError: (workflowId) =>
    set((s) => ({ errors: { ...s.errors, [workflowId]: null } })),

  reset: () =>
    set({ configByWorkflow: {}, loading: {}, saving: {}, errors: {} }),
}));
