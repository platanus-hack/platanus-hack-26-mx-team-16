import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpDocumentRepository } from "@/src/infrastructure/repositories/http-document";
import { HttpWorkflowDocumentRepository } from "@/src/infrastructure/repositories/http-workflow-document";
import { authHttp } from "@/src/infrastructure/http/client";
import { queryKeys } from "./keys";

const repo = new HttpDocumentRepository(authHttp);
const workflowDocRepo = new HttpWorkflowDocumentRepository(authHttp);

export function useDocumentsQuery(
  workflowUuid: string,
  options: { enabled?: boolean } = {}
) {
  return useQuery({
    queryKey: queryKeys.documents.all(workflowUuid),
    queryFn: async () => {
      const res = await repo.getAll(workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: options.enabled !== false && !!workflowUuid,
  });
}

export function useDocumentQuery(documentUuid: string) {
  return useQuery({
    queryKey: queryKeys.documents.detail(documentUuid),
    queryFn: async () => {
      const res = await repo.getById(documentUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!documentUuid,
  });
}

export function useWorkflowDocumentQuery(documentId: string) {
  return useQuery({
    queryKey: queryKeys.documents.workflowDocument(documentId),
    queryFn: async () => {
      const res = await workflowDocRepo.getById(documentId);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!documentId,
  });
}

export function useDeleteDocumentMutation(workflowUuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.documents.all(workflowUuid) }),
  });
}
