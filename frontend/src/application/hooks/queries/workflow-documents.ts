import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { queryKeys } from "@/src/application/hooks/queries/keys";
import { authHttp, localHttp } from "@/src/infrastructure/http/client";
import {
  HttpWorkflowDocumentRepository,
  type WorkflowDocumentDetail,
} from "@/src/infrastructure/repositories/http-workflow-document";

/**
 * E5 · Inspection Bench: carga del documento vía TanStack Query (reemplaza el
 * fetch manual de `document-detail-view`) + mutación de verificación por campo
 * vía BFF (`PATCH /api/workflows/{wf}/cases/{caseId}/documents/{id}/fields`).
 */

const repository = new HttpWorkflowDocumentRepository(authHttp);

export function useWorkflowDocumentQuery(documentId: string) {
  return useQuery({
    queryKey: queryKeys.documents.workflowDocument(documentId),
    queryFn: async () => {
      const res = await repository.getById(documentId);
      if (!("data" in res)) {
        throw new Error(res.errors[0]?.message ?? "Documento no encontrado");
      }
      return res.data;
    },
    enabled: !!documentId,
  });
}

/** 423 `case.locked`: la APPROVAL abierta del caso está reclamada por otro. */
export class CaseLockedError extends Error {
  readonly code = "case.locked";
  readonly holder: string | null;

  constructor(message: string, holder: string | null) {
    super(message);
    this.name = "CaseLockedError";
    this.holder = holder;
  }
}

export interface VerifyFieldInput {
  fieldPath: string;
  action: "correct" | "accept";
  value?: unknown;
}

export interface VerifyFieldsResult {
  document: WorkflowDocumentDetail;
  verifiedFields: string[];
  level: number;
  correctionsSignaled: boolean;
}

function parseVerifyFieldError(error: unknown): Error | null {
  if (!isAxiosError(error) || !error.response) return null;
  const data = error.response.data as
    | { errors?: Array<Record<string, unknown>> }
    | undefined;
  const first = data?.errors?.[0] ?? {};
  const code = typeof first.code === "string" ? first.code : null;
  const message =
    typeof first.message === "string"
      ? first.message
      : "No se pudo guardar el campo.";
  if (code === "case.locked") {
    const holder = typeof first.holder === "string" ? first.holder : null;
    return new CaseLockedError(message, holder);
  }
  if (code) return new Error(message);
  return null;
}

/**
 * Corrige (`correct`) o acepta (`accept`) campos del documento. Acepta uno o
 * varios items por llamada. Éxito ⇒ actualiza la caché del documento con el
 * presenter fresco que devuelve el backend e invalida el detalle del caso y
 * la cola de tareas (el run pausado pudo recibir la señal `corrections`).
 */
export function useVerifyFieldsMutation(
  workflowUuid: string,
  caseId: string,
  documentId: string
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: VerifyFieldInput | VerifyFieldInput[]) => {
      try {
        const res = await localHttp.patch<{ data: VerifyFieldsResult }>(
          `/workflows/${workflowUuid}/cases/${caseId}/documents/${documentId}/fields`,
          items
        );
        return res.data.data;
      } catch (error) {
        throw parseVerifyFieldError(error) ?? error;
      }
    },
    onSuccess: (result) => {
      qc.setQueryData(
        queryKeys.documents.workflowDocument(documentId),
        result.document
      );
      // El caso puede transicionar (corrections → re-analyze) y los gate
      // items de la tarea cambian: prefijo `cases` + humanTasks.
      qc.invalidateQueries({ queryKey: queryKeys.cases.all(workflowUuid) });
      qc.invalidateQueries({ queryKey: queryKeys.humanTasks.all });
    },
  });
}
