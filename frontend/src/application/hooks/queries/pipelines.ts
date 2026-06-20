import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";

import { authHttp } from "@/src/infrastructure/http/client";

import { queryKeys } from "./keys";

export interface Pipeline {
  uuid: string;
  /** Workflow propietario (ADR 0002: pipeline 1:1 con su workflow). */
  workflowId: string;
  slug: string;
  name: string;
  kind: string;
  status: string;
  currentVersion: number;
}

export interface PipelinePhase {
  id: string;
  kind: string;
  config: Record<string, unknown>;
}

// ── Policies (E6 §3) ─ camelCase NO se aplica al wire: el backend devuelve y
// acepta estas policies como JSON crudo con claves snake_case verbatim (son los
// nombres reales de los modelos pydantic). El FE las escribe de vuelta tal cual.
export interface ReviewStage {
  stage: "review_l1" | "review_l2";
  mode: "mandatory" | "by_exception";
}

export interface ActivationPolicy {
  field_thresholds?: Record<string, number>;
  on_low_confidence?: "clarify" | "review";
  blocking_rule_severities?: string[];
  sample_rate?: number;
  mode?: "mandatory" | "by_exception";
  stages?: ReviewStage[] | null;
  qa_sample_rate?: number;
}

// Las policies ya NO son version-level: completitud → `await_documents.config`,
// activación → `extraction_gate.config.activation` (D-A). Todo viaja en `phases`.
export interface PipelineVersion {
  pipelineId: string;
  version: number;
  phases: PipelinePhase[];
  outputSchema: Record<string, unknown> | null;
}

export interface PipelineVersionSummary {
  version: number;
  createdAt: string | null;
  phaseCount: number;
}

// ── Phase catalog (GET /v1/pipelines/phase-catalog) ──
// configSchema keys son snake_case verbatim (fan_out, ...).
export interface PhaseConfigField {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  enum?: string[];
  default?: unknown;
}

export interface PhaseCatalogEntry {
  kind: string;
  scope: "document" | "case";
  configSchema: Record<string, PhaseConfigField>;
  description: string;
}

// ── Publish / validate payloads ──
export interface PipelineRecipePayload {
  phases: PipelinePhase[];
  outputSchema?: Record<string, unknown> | null;
}

export interface DryRunResult {
  valid: boolean;
  summary: { phaseCount: number; kinds: string[] };
}

/**
 * Error estructurado del publish/dry-run del backend
 * (`{error, detail}` con 422). Se expone para que el editor pinte el detalle
 * inline en la tarjeta culpable.
 */
export interface PipelineValidationError {
  error: string;
  detail: string;
}

type Envelope<T> = { data: T } | { errors: { message: string }[] };

// ADR 0002 — el pipeline es propiedad 1:1 del workflow. Todas las rutas son
// workflow-scoped (las tenant-level /v1/pipelines fueron retiradas, salvo el
// phase-catalog). `authHttp` (baseURL "/api") va por el proxy que reescribe
// /api/v1/* al backend con X-Api-Key (ver src/proxy.ts).
const CATALOG_BASE = "/v1/pipelines";
// Las queries que llaman a esto van siempre con `enabled` ⇒ workflowId presente;
// el `?? ""` solo evita aserciones non-null y nunca llega a la red sin id.
const wfBase = (workflowId: string | null) =>
  `/v1/workflows/${workflowId ?? ""}/pipeline`;

function unwrap<T>(res: Envelope<T>): T {
  if ("errors" in res) throw new Error(res.errors[0]?.message);
  return res.data;
}

/**
 * Extrae `{error, detail}` de un 422 del publish/dry-run (o null). El backend
 * envuelve el error como `{data: {error, detail}, timestamp}`; antes solo se
 * miraba el nivel superior, así que el detalle real (p. ej. "await_documents
 * debe ser la PRIMERA fase case-scope") nunca llegaba a la UI y se caía al
 * mensaje genérico. Aceptamos ambas formas (envuelta y plana).
 */
export function asPipelineValidationError(
  err: unknown
): PipelineValidationError | null {
  const ax = err as AxiosError<unknown>;
  const body = ax?.response?.data as
    | { data?: unknown; error?: unknown; detail?: unknown }
    | undefined;
  const payload =
    body && typeof body === "object" && "data" in body && body.data
      ? (body.data as Record<string, unknown>)
      : (body as Record<string, unknown> | undefined);
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    "detail" in payload
  ) {
    return payload as unknown as PipelineValidationError;
  }
  return null;
}

function recipeBody(recipe: PipelineRecipePayload) {
  return {
    phases: recipe.phases,
    outputSchema: recipe.outputSchema ?? null,
  };
}

// ── Queries ──

/** Contenedor del pipeline del workflow (GET .../pipeline). */
export function useWorkflowPipelineQuery(workflowId: string | null) {
  return useQuery({
    queryKey: queryKeys.pipelines.byWorkflow(workflowId ?? ""),
    enabled: !!workflowId,
    queryFn: async () =>
      unwrap<Pipeline>((await authHttp.get(wfBase(workflowId))).data),
  });
}

export function useWorkflowPipelineVersionQuery(
  workflowId: string | null,
  version: number | null,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.pipelines.version(workflowId ?? "", version),
    enabled: (options?.enabled ?? true) && !!workflowId && version != null,
    queryFn: async () =>
      unwrap<PipelineVersion>(
        (await authHttp.get(`${wfBase(workflowId)}/versions/${version}`)).data
      ),
  });
}

export function useWorkflowPipelineVersionsQuery(
  workflowId: string | null,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.pipelines.versions(workflowId ?? ""),
    enabled: (options?.enabled ?? true) && !!workflowId,
    queryFn: async () =>
      unwrap<PipelineVersionSummary[]>(
        (await authHttp.get(`${wfBase(workflowId)}/versions`)).data
      ),
  });
}

export function usePhaseCatalogQuery() {
  return useQuery({
    queryKey: queryKeys.pipelines.catalog,
    // El catálogo es estable durante la sesión (deriva del registry Python).
    staleTime: 5 * 60 * 1000,
    queryFn: async () =>
      unwrap<PhaseCatalogEntry[]>(
        (await authHttp.get(`${CATALOG_BASE}/phase-catalog`)).data
      ),
  });
}

// ── Mutations ──

/**
 * Dry-run de la receta + policies (POST .../versions?validate_only=true).
 * No persiste; devuelve `{valid, summary}` (200) o lanza con un 422
 * `{error, detail}` legible por `asPipelineValidationError`.
 */
export function useValidateRecipeMutation(workflowId: string | null) {
  return useMutation({
    mutationFn: async (
      recipe: PipelineRecipePayload
    ): Promise<DryRunResult> => {
      const res = await authHttp.post(
        `${wfBase(workflowId)}/versions?validate_only=true`,
        recipeBody(recipe)
      );
      return res.data as DryRunResult;
    },
  });
}

/**
 * Publica una versión nueva (append-only) y avanza `current_version` al
 * instante en el backend. El editor debe mostrar el diff + confirmación ANTES.
 */
export function usePublishVersionMutation(workflowId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (recipe: PipelineRecipePayload) => {
      const res = await authHttp.post(
        `${wfBase(workflowId)}/versions`,
        recipeBody(recipe)
      );
      return res.data as Pipeline & { version: number };
    },
    onSuccess: () => {
      if (workflowId) {
        qc.invalidateQueries({
          queryKey: queryKeys.pipelines.byWorkflow(workflowId),
        });
        qc.invalidateQueries({
          queryKey: queryKeys.pipelines.versions(workflowId),
        });
      }
    },
  });
}

/**
 * E7 · F3 — wizard «agregar capacidad». Inserta las fases + scaffolds de policy
 * de la capacidad sobre la versión vigente y publica v+1 en el backend; refresca
 * el pipeline, las versiones y el propio workflow (sus `capabilities`).
 */
export function useAddCapabilityMutation(workflowId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (capability: string) => {
      // `wfBase` ya termina en `/pipeline` ⇒ la ruta es `.../pipeline/capabilities`.
      const res = await authHttp.post(`${wfBase(workflowId)}/capabilities`, {
        capability,
      });
      return res.data as Pipeline & {
        version: number;
        addedCapability: string;
        capabilities: string[];
      };
    },
    onSuccess: () => {
      if (!workflowId) return;
      qc.invalidateQueries({
        queryKey: queryKeys.pipelines.byWorkflow(workflowId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.pipelines.versions(workflowId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.workflows.detail(workflowId),
      });
    },
  });
}
