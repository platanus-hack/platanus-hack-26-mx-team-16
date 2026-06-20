import { create } from "zustand";
import type { Document } from "@/src/domain/entities/document";
import { DocumentStatus } from "@/src/domain/entities/document";
import type { Workflow } from "@/src/domain/entities/workflow";
import { MockDocumentRepository } from "@/src/infrastructure/repositories/mock-document";
import { HttpWorkflowRepository } from "@/src/infrastructure/repositories/http-workflow";
import { authHttp } from "@/src/infrastructure/http/client";

const documentRepository = new MockDocumentRepository();
const workflowRepository = new HttpWorkflowRepository(authHttp);

export type DocumentFilterTab = "all" | DocumentStatus;

interface WorkflowDocumentsState {
  workflow: Workflow | null;
  documents: Document[];
  selectedDocument: Document | null;
  isLoading: boolean;
  isLoadingDocument: boolean;
  error: string | null;
  currentFilter: DocumentFilterTab;

  // Actions
  loadWorkflow: (workflowUuid: string) => Promise<void>;
  loadDocuments: (workflowUuid: string) => Promise<void>;
  loadDocument: (documentUuid: string) => Promise<void>;
  deleteDocument: (uuid: string) => Promise<void>;
  setFilter: (filter: DocumentFilterTab) => void;
  getFilteredDocuments: () => Document[];
  reset: () => void;
}

export const useWorkflowDocumentsStore = create<WorkflowDocumentsState>(
  (set, get) => ({
    workflow: null,
    documents: [],
    selectedDocument: null,
    isLoading: false,
    isLoadingDocument: false,
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

    loadDocuments: async (workflowUuid: string) => {
      set({ isLoading: true, error: null });
      const response = await documentRepository.getAll(workflowUuid);
      if ("data" in response) {
        set({ documents: response.data });
      } else if ("errors" in response) {
        set({
          error: response.errors[0]?.message || "Failed to load documents",
        });
      }
      set({ isLoading: false });
    },

    loadDocument: async (documentUuid: string) => {
      set({ isLoadingDocument: true, error: null });
      const response = await documentRepository.getById(documentUuid);
      if ("data" in response) {
        set({ selectedDocument: response.data });
      } else if ("errors" in response) {
        set({
          error: response.errors[0]?.message || "Failed to load document",
        });
      }
      set({ isLoadingDocument: false });
    },

    deleteDocument: async (uuid: string) => {
      const response = await documentRepository.delete(uuid);
      if ("success" in response) {
        const currentWorkflow = get().workflow;
        if (currentWorkflow) {
          await get().loadDocuments(currentWorkflow.uuid);
        }
      }
    },

    setFilter: (filter: DocumentFilterTab) => {
      set({ currentFilter: filter });
    },

    getFilteredDocuments: () => {
      const { documents, currentFilter } = get();
      if (currentFilter === "all") {
        return documents;
      }
      return documents.filter((doc) => doc.status === currentFilter);
    },

    reset: () => {
      set({
        workflow: null,
        documents: [],
        selectedDocument: null,
        isLoading: false,
        isLoadingDocument: false,
        error: null,
        currentFilter: "all",
      });
    },
  })
);
