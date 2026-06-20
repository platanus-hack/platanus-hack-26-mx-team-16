import { create } from "zustand";
import type { SetView } from "@/src/application/hooks/use-processing-job-events";
import type { CaseDetail } from "@/src/domain/entities/case";
import {
  isWorkflowProcessingJobInFlight,
  isWorkflowProcessingJobTerminal,
  type WorkflowProcessingJobStatus,
} from "@/src/domain/events/processing-job-event";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpCaseRepository } from "@/src/infrastructure/repositories/http-case";

const caseRepository = new HttpCaseRepository(authHttp);

interface WorkflowCaseDetailState {
  caseDetail: CaseDetail | null;
  isLoading: boolean;
  error: string | null;
  /** Last seen status per set; used to detect in-flight → terminal transitions. */
  lastSetStatuses: Map<string, WorkflowProcessingJobStatus>;

  loadCase: (workflowUuid: string, caseId: string) => Promise<void>;
  updateName: (
    workflowUuid: string,
    caseId: string,
    name: string
  ) => Promise<void>;
  /**
   * Snapshot incoming SSE sets and refetch the case detail when any set
   * has transitioned from in-flight to terminal since the last snapshot.
   * The transition contract: per-document data behind `documentGroups`
   * only lands in PG once the workflow's extract/validate steps commit,
   * so we re-pull the case after each observed transition.
   */
  observeSets: (workflowUuid: string, caseId: string, sets: SetView[]) => void;
  reset: () => void;
}

export const useWorkflowCaseDetailStore = create<WorkflowCaseDetailState>(
  (set, get) => ({
    caseDetail: null,
    isLoading: true,
    error: null,
    lastSetStatuses: new Map(),

    loadCase: async (workflowUuid, caseId) => {
      set({ isLoading: true, error: null });
      const response = await caseRepository.getById(workflowUuid, caseId);
      if ("data" in response) {
        set({ caseDetail: response.data, isLoading: false });
      } else if ("errors" in response) {
        set({
          error: response.errors[0]?.message || "Failed to load case",
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
    },

    updateName: async (workflowUuid, caseId, name) => {
      const response = await caseRepository.update(workflowUuid, caseId, {
        name,
      });
      if ("data" in response) {
        set((state) => ({
          caseDetail: state.caseDetail
            ? { ...state.caseDetail, name: response.data.name }
            : state.caseDetail,
        }));
      }
    },

    observeSets: (workflowUuid, caseId, sets) => {
      const prev = get().lastSetStatuses;
      const next = new Map<string, WorkflowProcessingJobStatus>();
      let justFinished = false;
      for (const s of sets) {
        next.set(s.setId, s.status);
        const before = prev.get(s.setId);
        if (
          before !== undefined &&
          isWorkflowProcessingJobInFlight(before) &&
          isWorkflowProcessingJobTerminal(s.status)
        ) {
          justFinished = true;
        }
      }
      set({ lastSetStatuses: next });
      if (justFinished) {
        void get().loadCase(workflowUuid, caseId);
      }
    },

    reset: () => {
      set({
        caseDetail: null,
        isLoading: true,
        error: null,
        lastSetStatuses: new Map(),
      });
    },
  })
);
