import { create } from "zustand";
import type { Case } from "@/src/domain/entities/case";
import { CaseStatus } from "@/src/domain/entities/case";
import type { Workflow } from "@/src/domain/entities/workflow";
import { HttpCaseRepository } from "@/src/infrastructure/repositories/http-case";
import { HttpWorkflowRepository } from "@/src/infrastructure/repositories/http-workflow";
import { authHttp } from "@/src/infrastructure/http/client";

const caseRepository = new HttpCaseRepository(authHttp);
const workflowRepository = new HttpWorkflowRepository(authHttp);

export type CaseFilterTab = "all" | CaseStatus;

interface WorkflowCasesState {
  workflow: Workflow | null;
  cases: Case[];
  isLoading: boolean;
  error: string | null;
  currentFilter: CaseFilterTab;

  loadWorkflow: (workflowUuid: string) => Promise<void>;
  loadCases: (workflowUuid: string) => Promise<void>;
  createCase: (workflowUuid: string, name: string) => Promise<void>;
  deleteCase: (caseUuid: string) => Promise<void>;
  setFilter: (filter: CaseFilterTab) => void;
  getFilteredCases: () => Case[];
  reset: () => void;
}

export const useWorkflowCasesStore = create<WorkflowCasesState>((set, get) => ({
  workflow: null,
  cases: [],
  isLoading: false,
  error: null,
  currentFilter: "all",

  loadWorkflow: async (workflowUuid: string) => {
    const current = get().workflow;
    if (current?.uuid === workflowUuid) return;

    set({ isLoading: true, error: null });
    const response = await workflowRepository.getById(workflowUuid);
    if ("data" in response) {
      set({ workflow: response.data });
    } else if ("errors" in response) {
      set({
        error: response.errors[0]?.message || "Failed to load workflow",
      });
    }
    set({ isLoading: false });
  },

  loadCases: async (workflowUuid: string) => {
    set({ isLoading: true, error: null });
    const response = await caseRepository.getAll(workflowUuid);
    if ("data" in response) {
      set({ cases: response.data });
    } else if ("errors" in response) {
      set({
        error: response.errors[0]?.message || "Failed to load cases",
      });
    }
    set({ isLoading: false });
  },

  createCase: async (workflowUuid: string, name: string) => {
    const response = await caseRepository.create(workflowUuid, { name });
    if ("data" in response) {
      set((state) => ({ cases: [response.data, ...state.cases] }));
    }
  },

  deleteCase: async (caseUuid: string) => {
    const { workflow } = get();
    if (!workflow) return;
    const response = await caseRepository.delete(workflow.uuid, caseUuid);
    if ("data" in response) {
      set((state) => ({
        cases: state.cases.filter((c) => c.uuid !== caseUuid),
      }));
    }
  },

  setFilter: (filter: CaseFilterTab) => {
    set({ currentFilter: filter });
  },

  getFilteredCases: () => {
    const { cases, currentFilter } = get();
    if (currentFilter === "all") {
      return cases;
    }
    return cases.filter((c) => c.status === currentFilter);
  },

  reset: () => {
    set({
      workflow: null,
      cases: [],
      isLoading: false,
      error: null,
      currentFilter: "all",
    });
  },
}));
