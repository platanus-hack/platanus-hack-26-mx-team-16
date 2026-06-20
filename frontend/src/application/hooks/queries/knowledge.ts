import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpKnowledgeDocumentRepository } from "@/src/infrastructure/repositories/http-knowledge-document";
import { MockKnowledgeRepository } from "@/src/infrastructure/repositories/mock-knowledge";
import { authHttp } from "@/src/infrastructure/http/client";
import { queryKeys } from "./keys";

const repo = new HttpKnowledgeDocumentRepository(authHttp);
const knowledgeBaseRepo = new MockKnowledgeRepository();

export function useKnowledgeQuery() {
  return useQuery({
    queryKey: queryKeys.knowledge.all,
    queryFn: async () => {
      const res = await repo.getAll();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useWorkflowKnowledgeQuery(workflowId: string) {
  return useQuery({
    queryKey: queryKeys.knowledge.byWorkflow(workflowId),
    queryFn: async () => {
      const res = await repo.listByWorkflow(workflowId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!workflowId,
  });
}

export function useUploadKnowledgeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const res = await repo.upload(file);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.knowledge.all }),
  });
}

export function useUploadWorkflowKnowledgeMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const res = await repo.uploadToWorkflow(workflowId, file);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.knowledge.byWorkflow(workflowId),
      }),
  });
}

export function useDeleteKnowledgeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.knowledge.all }),
  });
}

export function useDeleteWorkflowKnowledgeMutation(workflowId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.deleteFromWorkflow(workflowId, uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.knowledge.byWorkflow(workflowId),
      }),
  });
}

export function useKnowledgeBasesQuery() {
  return useQuery({
    queryKey: queryKeys.knowledgeBases.all,
    queryFn: async () => {
      const res = await knowledgeBaseRepo.getAll();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useDuplicateKnowledgeBaseMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await knowledgeBaseRepo.duplicate(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.knowledgeBases.all }),
  });
}

export function useDeleteKnowledgeBaseMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await knowledgeBaseRepo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.knowledgeBases.all }),
  });
}
