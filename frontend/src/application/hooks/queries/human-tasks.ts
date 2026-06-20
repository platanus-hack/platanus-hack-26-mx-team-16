import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { queryKeys } from "@/src/application/hooks/queries/keys";
import { authHttp } from "@/src/infrastructure/http/client";

// E5 · colas L1/L2: stages de revisión multinivel.
export type ReviewStage = "review_l1" | "review_l2";

export interface HumanTask {
  uuid: string;
  taskKey: string;
  kind: string;
  status: string;
  assigneeMode: string;
  audience: string | null;
  caseId: string | null;
  workflowId: string | null;
  workflowSlug: string | null;
  payload: Record<string, unknown> | null;
  createdAt: string | null;
  // E5 · revisión multinivel + lock pesimista.
  stage: ReviewStage | null;
  claimedBy: string | null; // "user:<uuid>" | "staff:<uuid>"
  claimedAt: string | null;
}

/** E5 · campo flageado sin verificar (409 `human_task.open_flags`). */
export interface OpenFlagField {
  documentId: string;
  fieldPath: string;
}

export class HumanTaskOpenFlagsError extends Error {
  readonly code = "human_task.open_flags";
  readonly openFields: OpenFlagField[];

  constructor(message: string, openFields: OpenFlagField[]) {
    super(message);
    this.name = "HumanTaskOpenFlagsError";
    this.openFields = openFields;
  }
}

export class HumanTaskClaimedError extends Error {
  readonly code = "human_task.already_claimed";
  readonly holder: string | null;

  constructor(message: string, holder: string | null) {
    super(message);
    this.name = "HumanTaskClaimedError";
    this.holder = holder;
  }
}

/**
 * Traduce los 409 de claim/resolve (E5 §3.2/§3.4) a errores tipados. El
 * envelope es `{errors: [{code, message, openFields?, holder?}]}` — tolerante
 * a variantes, igual que `parseNotComplete` en case-readiness.
 */
function parseHumanTaskConflict(error: unknown): Error | null {
  if (!isAxiosError(error) || !error.response) return null;
  const data = error.response.data as
    | { errors?: Array<Record<string, unknown>> }
    | undefined;
  const first = data?.errors?.[0] ?? {};
  const code = typeof first.code === "string" ? first.code : null;
  const message =
    typeof first.message === "string" ? first.message : "Conflicto al resolver";

  if (code === "human_task.open_flags") {
    const raw = Array.isArray(first.openFields) ? first.openFields : [];
    const openFields = raw
      .filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null
      )
      .map((item) => ({
        documentId: String(item.documentId ?? ""),
        fieldPath: String(item.fieldPath ?? ""),
      }));
    return new HumanTaskOpenFlagsError(message, openFields);
  }
  if (code === "human_task.already_claimed") {
    const holder = typeof first.holder === "string" ? first.holder : null;
    return new HumanTaskClaimedError(message, holder);
  }
  if (code) return new Error(message);
  return null;
}

type Envelope<T> = { data: T } | { errors: { message: string }[] };

const BASE = "/v1/human-tasks";

const api = {
  list: async (audience?: string): Promise<Envelope<HumanTask[]>> =>
    (
      await authHttp.get(BASE, {
        params: audience ? { audience } : undefined,
      })
    ).data,
  resolve: async (
    id: string,
    resolution: Record<string, unknown>
  ): Promise<Envelope<unknown>> =>
    (await authHttp.post(`${BASE}/${id}/resolve`, { resolution })).data,
  claim: async (id: string, release: boolean): Promise<Envelope<HumanTask>> =>
    (await authHttp.post(`${BASE}/${id}/claim`, { release })).data,
};

export function useHumanTasksQuery(audience?: string) {
  return useQuery({
    queryKey: queryKeys.humanTasks.list(audience),
    queryFn: async () => {
      const res = await api.list(audience);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useResolveHumanTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      id: string;
      resolution: Record<string, unknown>;
    }) => {
      try {
        const res = await api.resolve(input.id, input.resolution);
        if ("errors" in res) throw new Error(res.errors[0]?.message);
        return res.data;
      } catch (error) {
        // E5 §3.2/§3.4: 409 open_flags ⇒ force-dialog; 409 already_claimed
        // ⇒ holder visible. El resto conserva el mensaje del backend.
        throw parseHumanTaskConflict(error) ?? error;
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.humanTasks.all });
      // Resolver una tarea (approve/reject/clarify) mueve el estado del
      // caso; las keys de casos usan wfSlug y la tarea trae workflowId
      // (uuid), así que invalidamos el prefijo completo.
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

/**
 * E5 §3.2 · claim/release pesimista. `release: true` libera (solo el holder
 * o un admin del tenant). 409 `human_task.already_claimed` ⇒
 * `HumanTaskClaimedError` con el holder para pintarlo en la UI.
 */
export function useClaimHumanTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string; release?: boolean }) => {
      try {
        const res = await api.claim(input.id, input.release ?? false);
        if ("errors" in res) throw new Error(res.errors[0]?.message);
        return res.data;
      } catch (error) {
        throw parseHumanTaskConflict(error) ?? error;
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.humanTasks.all });
    },
  });
}
