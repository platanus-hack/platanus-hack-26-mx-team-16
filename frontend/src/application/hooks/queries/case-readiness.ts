import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { queryKeys } from "@/src/application/hooks/queries/keys";
import type {
  CaseCompleteness,
  CaseCompletenessMissing,
} from "@/src/domain/entities/case";
import { localHttp } from "@/src/infrastructure/http/client";

/**
 * E4 · Readiness del expediente, vía BFF:
 *   POST /api/workflows/{slug}/cases/{caseId}/ready        → marcar listo
 *   GET  /api/workflows/{slug}/cases/{caseId}/completeness → cálculo fresco
 */

export const CASE_NOT_COMPLETE_CODE = "case.not_complete";

/** 409 del backend cuando faltan documentos requeridos y `force` es false. */
export class CaseNotCompleteError extends Error {
  readonly code = CASE_NOT_COMPLETE_CODE;
  readonly missing: CaseCompletenessMissing[];

  constructor(message: string, missing: CaseCompletenessMissing[]) {
    super(message);
    this.name = "CaseNotCompleteError";
    this.missing = missing;
  }
}

/**
 * Único punto de mapping del 409 `case.not_complete`: el backend está en
 * construcción, así que toleramos el code/missing tanto en el error item
 * (`errors[0]`) como a nivel de payload.
 */
function parseNotComplete(data: unknown): CaseNotCompleteError | null {
  if (typeof data !== "object" || data === null) return null;
  const payload = data as Record<string, unknown>;
  const firstError = Array.isArray(payload.errors)
    ? ((payload.errors[0] ?? {}) as Record<string, unknown>)
    : {};

  const code = (firstError.code ?? payload.code) as string | undefined;
  if (code !== CASE_NOT_COMPLETE_CODE) return null;

  const rawMissing =
    firstError.missing ??
    payload.missing ??
    (payload.detail as Record<string, unknown> | undefined)?.missing;
  const missing: CaseCompletenessMissing[] = Array.isArray(rawMissing)
    ? rawMissing
        .filter(
          (item): item is Record<string, unknown> =>
            typeof item === "object" && item !== null
        )
        .map((item) => ({
          documentType: String(item.documentType ?? ""),
          missing: Number(item.missing ?? 0),
        }))
    : [];

  const message =
    (firstError.message as string | undefined) ??
    "El expediente aún no está completo.";
  return new CaseNotCompleteError(message, missing);
}

export function useMarkCaseReadyMutation(
  workflowUuid: string,
  caseId: string
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ force = false }: { force?: boolean } = {}) => {
      try {
        const res = await localHttp.post<{ data?: unknown }>(
          `/workflows/${workflowUuid}/cases/${caseId}/ready`,
          { force }
        );
        return res.data?.data ?? res.data;
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 409) {
          const notComplete = parseNotComplete(error.response.data);
          if (notComplete) throw notComplete;
        }
        if (isAxiosError(error)) {
          const data = error.response?.data as
            | { errors?: { message?: string }[] }
            | undefined;
          throw new Error(
            data?.errors?.[0]?.message ?? "No se pudo marcar el caso como listo."
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      // `cases.all` es prefijo de detail/paginated/completeness; añadimos
      // human tasks porque el pipeline puede generar tareas al avanzar.
      qc.invalidateQueries({ queryKey: queryKeys.cases.all(workflowUuid) });
      qc.invalidateQueries({ queryKey: queryKeys.humanTasks.all });
    },
  });
}

export function useCaseCompletenessQuery(
  workflowUuid: string,
  caseId: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.cases.completeness(workflowUuid, caseId),
    queryFn: async () => {
      const res = await localHttp.get<{ data: CaseCompleteness }>(
        `/workflows/${workflowUuid}/cases/${caseId}/completeness`
      );
      return res.data.data;
    },
    enabled: (options?.enabled ?? true) && !!workflowUuid && !!caseId,
  });
}
