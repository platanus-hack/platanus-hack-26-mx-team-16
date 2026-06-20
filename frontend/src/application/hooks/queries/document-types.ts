import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HttpDocumentTypeRepository } from "@/src/infrastructure/repositories/http-doctype";
import { authHttp } from "@/src/infrastructure/http/client";
import type {
  CreateDocumentTypePayload,
  SuggestFieldsPayload,
  UpdateDocumentTypePayload,
} from "@/src/domain/repositories/doctype";
import { queryKeys } from "./keys";

const repo = new HttpDocumentTypeRepository(authHttp);

export function useDocumentTypesQuery(workflowUuid?: string) {
  return useQuery({
    queryKey: queryKeys.documentTypes.all(workflowUuid),
    queryFn: async () => {
      const res = await repo.getAll(workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useDocumentTypeQuery(uuid: string) {
  return useQuery({
    queryKey: queryKeys.documentTypes.detail(uuid),
    queryFn: async () => {
      const res = await repo.getById(uuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    enabled: !!uuid,
  });
}

export function useCreateDocumentTypeMutation(workflowUuid?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateDocumentTypePayload) => {
      const res = await repo.create(payload, workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.documentTypes.all(workflowUuid),
      }),
  });
}

export function useUpdateDocumentTypeMutation(uuid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateDocumentTypePayload) => {
      const res = await repo.update(uuid, payload);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.documentTypes.detail(uuid) });
      qc.invalidateQueries({ queryKey: queryKeys.documentTypes.all() });
    },
  });
}

export function useDeleteDocumentTypeMutation(workflowUuid?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (uuid: string) => {
      const res = await repo.delete(uuid, workflowUuid);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.documentTypes.all(workflowUuid),
      }),
  });
}

export function useSuggestFieldsMutation() {
  return useMutation({
    mutationFn: async ({
      doctypeId,
      prompt,
    }: SuggestFieldsPayload & { doctypeId: string }): Promise<void> => {
      const res = await repo.suggestFields(doctypeId, { prompt });
      if ("errors" in res)
        throw new Error(res.errors[0]?.message ?? "Error al sugerir campos");
    },
  });
}
