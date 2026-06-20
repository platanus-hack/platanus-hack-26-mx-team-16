import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";

import { queryKeys } from "@/src/application/hooks/queries/keys";
import type { CaseEvent } from "@/src/domain/entities/case";
import { localHttp } from "@/src/infrastructure/http/client";
import type { MappedExtraction } from "@/src/infrastructure/repositories/http-workflow-document";

/**
 * E5 · consola staff (ADR 0001). Tipos espejo de los presenters de
 * `backend/src/staff/presentation/presenters.py` (camelCase en el wire,
 * blobs RawJson — mappedExtraction/payload conservan sus claves de dominio).
 * Red: BFF `/api/staff/*` vía `localHttp` (adjunta Authorization; el BFF
 * descarta X-Tenant — la superficie staff es cross-tenant).
 */

export interface StaffTask {
  uuid: string;
  taskKey: string;
  kind: string;
  status: string;
  stage: string | null;
  assigneeMode: string;
  audience: string | null;
  caseId: string | null;
  workflowId: string | null;
  tenantId: string;
  tenantName: string | null;
  tenantSlug: string | null;
  claimedBy: string | null;
  claimedAt: string | null;
  payload: Record<string, unknown> | null;
  createdAt: string | null;
}

export interface StaffCaseDocument {
  documentId: string;
  documentTypeId: string | null;
  source: string | null;
  status: string | null;
  fileName: string | null;
  mappedExtraction: MappedExtraction | null;
  fieldConfidence: Record<string, number> | null;
  needsClarification: Record<string, unknown> | unknown[] | null;
  verification: Record<
    string,
    {
      value?: unknown;
      verified_by?: string;
      level?: number;
      verified_at?: string;
      previous_value?: unknown;
    }
  > | null;
}

export interface StaffCaseRun {
  runId: string;
  status: string;
  trigger: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface StaffCaseAggregate {
  caseId: string;
  workflowId: string;
  tenantId: string;
  tenantName: string | null;
  tenantSlug: string | null;
  name: string | null;
  status: string;
  externalRef: string | null;
  createdAt: string | null;
  readyAt: string | null;
  readOnly: boolean;
  documents: StaffCaseDocument[];
  runs: StaffCaseRun[];
  latestOutput: {
    verdict: string | null;
    confidenceScore: number | null;
    narrativeStatus: string | null;
    hasOutput: boolean;
  } | null;
  timeline: CaseEvent[];
}

export interface StaffAuditEvent {
  uuid: string;
  staffUserId: string;
  action: string;
  tenantId: string | null;
  caseId: string | null;
  taskId: string | null;
  requestId: string | null;
  ip: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string | null;
}

export interface StaffTaskFilters {
  tenant?: string;
  status?: string;
  /** E6 §3 — `qa` (auditoría) | `approval`; sin valor = ambos. */
  kind?: string;
  limit?: number;
}

/**
 * E6 · W8 — métricas QA/aprobaciones (`GET /staff/v1/metrics`, staff_admin).
 * Los cortes (`byTenant`/`byActor`) son dicts keyed por id; el presenter usa
 * RawJson, por eso no se camelizan los conteos internos. Tipos contados:
 * qa.passed, qa.failed, qa.sampled, review.approved, review.skipped.
 */
export interface StaffMetrics {
  since: string;
  totals: Record<string, number>;
  byTenant: Record<string, Record<string, number>>;
  byActor: Record<string, Record<string, number>>;
}

export interface StaffMetricsFilters {
  tenant?: string;
  since?: string;
}

export interface StaffAuditFilters {
  action?: string;
  tenant?: string;
  limit?: number;
  offset?: number;
}

type Envelope<T> = { data: T };

/** Código de error del envelope del backend (reflejado por el BFF). */
export function backendErrorCode(error: unknown): string | null {
  const data = (error as AxiosError)?.response?.data as
    | { errors?: { code?: string; message?: string }[] }
    | undefined;
  return data?.errors?.[0]?.code ?? null;
}

export function backendErrorMessage(error: unknown): string {
  const data = (error as AxiosError)?.response?.data as
    | { errors?: { code?: string; message?: string }[] }
    | undefined;
  return (
    data?.errors?.[0]?.message ??
    (error instanceof Error ? error.message : "Error inesperado")
  );
}

const api = {
  tasks: async (filters: StaffTaskFilters): Promise<StaffTask[]> =>
    (
      await localHttp.get<Envelope<StaffTask[]>>("/staff/tasks", {
        params: filters,
      })
    ).data.data,
  claim: async (taskId: string, release: boolean): Promise<StaffTask> =>
    (
      await localHttp.post<Envelope<StaffTask>>(`/staff/tasks/${taskId}/claim`, {
        release,
      })
    ).data.data,
  resolve: async (
    taskId: string,
    resolution: Record<string, unknown>
  ): Promise<StaffTask> =>
    (
      await localHttp.post<Envelope<StaffTask>>(
        `/staff/tasks/${taskId}/resolve`,
        { resolution }
      )
    ).data.data,
  case: async (caseId: string): Promise<StaffCaseAggregate> =>
    (
      await localHttp.get<Envelope<StaffCaseAggregate>>(
        `/staff/cases/${caseId}`
      )
    ).data.data,
  audit: async (filters: StaffAuditFilters): Promise<StaffAuditEvent[]> =>
    (
      await localHttp.get<Envelope<StaffAuditEvent[]>>("/staff/audit", {
        params: filters,
      })
    ).data.data,
  metrics: async (filters: StaffMetricsFilters): Promise<StaffMetrics> => {
    const raw = (
      await localHttp.get<Envelope<Record<string, unknown>>>("/staff/metrics", {
        params: filters,
      })
    ).data.data;
    // El presenter expone `by_tenant`/`by_actor` (RawJson, snake_case en wire);
    // normalizamos a camelCase aceptando ambas claves por robustez.
    return {
      since: String(raw.since ?? ""),
      totals: (raw.totals ?? {}) as Record<string, number>,
      byTenant: (raw.byTenant ?? raw.by_tenant ?? {}) as Record<
        string,
        Record<string, number>
      >,
      byActor: (raw.byActor ?? raw.by_actor ?? {}) as Record<
        string,
        Record<string, number>
      >,
    };
  },
};

export function useStaffTasksQuery(
  filters: StaffTaskFilters = {},
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.staff.tasks(filters),
    queryFn: () => api.tasks(filters),
    refetchInterval: 30_000,
    enabled: options?.enabled ?? true,
  });
}

export function useClaimStaffTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { taskId: string; release?: boolean }) =>
      api.claim(input.taskId, Boolean(input.release)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.staff.tasks() });
    },
  });
}

export function useResolveStaffTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      taskId: string;
      resolution: Record<string, unknown>;
    }) => api.resolve(input.taskId, input.resolution),
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: queryKeys.staff.tasks() });
      if (task.caseId) {
        qc.invalidateQueries({ queryKey: queryKeys.staff.case(task.caseId) });
      }
    },
  });
}

export function useStaffCaseQuery(caseId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.staff.case(caseId ?? "missing"),
    queryFn: () => api.case(caseId as string),
    enabled: Boolean(caseId),
  });
}

export function useStaffAuditQuery(
  filters: StaffAuditFilters = {},
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.staff.audit(filters),
    queryFn: () => api.audit(filters),
    enabled: options?.enabled ?? true,
  });
}

export function useStaffMetricsQuery(
  filters: StaffMetricsFilters = {},
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.staff.metrics(filters),
    queryFn: () => api.metrics(filters),
    enabled: options?.enabled ?? true,
  });
}
