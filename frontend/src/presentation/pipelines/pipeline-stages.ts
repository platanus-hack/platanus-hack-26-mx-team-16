import type {
  PhaseCatalogEntry,
  PipelinePhase,
} from "@/src/application/hooks/queries/pipelines";

/**
 * Agrupación de fases en ETAPAS — capa PURAMENTE presentacional (diseño
 * `product/plans/pipeline/mockups/fases-agrupadas.html`). El motor ejecuta una lista plana de
 * fases con un tag de scope; las etapas se derivan del `kind` (+ `config.trigger`
 * para distinguir la revisión gateada de la aprobación final). Cero impacto en
 * golden / validate_phases / runtime — solo cambia cómo se ve el editor.
 *
 * Bandas de scope en la UI: «Por documento» (corre por archivo) y «Por caso»
 * (corre una vez por caso). El código del motor sigue usando document/case.
 */

export type StageScope = "document" | "case";
export type StageKind = "group" | "solo";

export interface StageDef {
  id: string;
  /** Nombre amable en la UI. */
  label: string;
  description: string;
  scope: StageScope;
  /** group = contenedor de varias fases acopladas; solo = una sola fase. */
  kind: StageKind;
  /** El bloque entra/sale como unidad (output+deliver). */
  atomic?: boolean;
  /** Kinds de fase que pertenecen a esta etapa. */
  phaseKinds: readonly string[];
}

// Orden canónico de las etapas (document-scope primero, igual que el motor).
export const STAGE_DEFS: readonly StageDef[] = [
  {
    id: "extraction",
    label: "Extracción",
    description:
      "Procesa cada archivo y extrae sus campos. Al terminar emite `document.extracted`.",
    scope: "document",
    kind: "group",
    phaseKinds: [
      "ingest",
      "extract_text",
      "classify_pages",
      "extract_fields",
      "assess",
      "validate_extraction",
      "finalize",
    ],
  },
  {
    id: "completeness",
    label: "Completitud",
    description:
      "Mantiene el caso recibiendo documentos hasta cumplir el expediente.",
    scope: "case",
    kind: "solo",
    phaseKinds: ["await_documents"],
  },
  {
    id: "quality",
    label: "Control de calidad",
    description:
      "Compuerta de extracción + pausa de aclaración opcional (case-scope).",
    scope: "case",
    kind: "group",
    phaseKinds: ["extraction_gate", "await_clarification"],
  },
  {
    id: "enrichment",
    label: "Enriquecimiento",
    description:
      "Llama herramientas externas firmadas y persiste el resultado.",
    scope: "case",
    kind: "solo",
    phaseKinds: ["enrich"],
  },
  {
    id: "analysis",
    label: "Análisis",
    description: "Evalúa las reglas de negocio sobre los datos del caso.",
    scope: "case",
    kind: "solo",
    phaseKinds: ["analyze"],
  },
  {
    id: "approval",
    label: "Aprobación",
    description: "Cola de revisión/aprobación final antes de entregar.",
    scope: "case",
    kind: "solo",
    phaseKinds: ["human_review"],
  },
  {
    id: "output",
    label: "Salida",
    description:
      "Proyecta el output estructurado y lo entrega (`case.output.ready`).",
    scope: "case",
    kind: "group",
    atomic: true,
    phaseKinds: ["output", "deliver"],
  },
];

const STAGE_BY_ID = new Map(STAGE_DEFS.map((s) => [s.id, s]));

// Nombres amables de cada fase (el `kind` técnico queda como subtítulo mono).
const PHASE_LABELS: Record<string, string> = {
  ingest: "Ingesta",
  extract_text: "Extraer texto (OCR)",
  classify_pages: "Clasificar páginas",
  extract_fields: "Extraer campos",
  assess: "Confianza capa-2",
  validate_extraction: "Validar extracción",
  finalize: "Finalizar",
  await_documents: "Esperar documentos",
  extraction_gate: "Compuerta de extracción",
  await_clarification: "Aclaración",
  human_review: "Revisión humana",
  enrich: "Enriquecimiento",
  analyze: "Análisis",
  output: "Construir salida",
  deliver: "Entregar",
};

// Fases base de la extracción: siempre presentes, no se pueden quitar.
const BASE_PHASE_KINDS = new Set([
  "ingest",
  "extract_text",
  "classify_pages",
  "extract_fields",
  "finalize",
]);

export function phaseLabel(kind: string): string {
  return PHASE_LABELS[kind] ?? kind;
}

export function isBasePhase(kind: string): boolean {
  return BASE_PHASE_KINDS.has(kind);
}

/**
 * Una fase activa pero sin configurar no-opera o falla en silencio. Hoy el caso
 * conocido es `enrich` sin una herramienta elegida (`config.tool`).
 */
export function phaseNeedsConfig(phase: PipelinePhase): boolean {
  if (phase.kind === "enrich") return !phase.config?.tool;
  return false;
}

/**
 * Etapa a la que pertenece una fase. `human_review` es siempre la Aprobación
 * final (el gate de extracción ya no usa `human_review`).
 */
export function stageIdForPhase(phase: PipelinePhase): string {
  if (phase.kind === "human_review") {
    return "approval";
  }
  const owner = STAGE_DEFS.find(
    (s) => s.id !== "approval" && s.phaseKinds.includes(phase.kind)
  );
  return owner?.id ?? "extraction";
}

export interface StageGroup {
  def: StageDef;
  phases: PipelinePhase[];
}

export interface ScopeBand {
  scope: StageScope;
  /** Etiqueta de la banda en la UI (decisión 2026-06-13). */
  label: string;
  stages: StageGroup[];
}

const BAND_LABEL: Record<StageScope, string> = {
  document: "Por documento",
  case: "Por caso",
};

/**
 * Agrupa la lista plana de fases en bandas → etapas → fases (preservando el
 * orden original de las fases dentro de cada etapa). Solo devuelve las etapas
 * que tienen al menos una fase presente (etapas activas).
 */
export function groupPhasesIntoStages(
  phases: PipelinePhase[],
  _catalog: PhaseCatalogEntry[]
): ScopeBand[] {
  const byStage = new Map<string, PipelinePhase[]>();
  for (const phase of phases) {
    const stageId = stageIdForPhase(phase);
    const bucket = byStage.get(stageId);
    if (bucket) bucket.push(phase);
    else byStage.set(stageId, [phase]);
  }

  const bands: Record<StageScope, ScopeBand> = {
    document: { scope: "document", label: BAND_LABEL.document, stages: [] },
    case: { scope: "case", label: BAND_LABEL.case, stages: [] },
  };

  for (const def of STAGE_DEFS) {
    const stagePhases = byStage.get(def.id);
    if (!stagePhases?.length) continue;
    bands[def.scope].stages.push({ def, phases: stagePhases });
  }

  return [bands.document, bands.case].filter((b) => b.stages.length > 0);
}

export function stageById(id: string): StageDef | undefined {
  return STAGE_BY_ID.get(id);
}

/** ¿La fase corre en el scope de caso (banda «Por caso»)? */
export function isCaseScopePhase(phase: PipelinePhase): boolean {
  return stageById(stageIdForPhase(phase))?.scope === "case";
}

/**
 * Cola canónica al activar el scope de caso desde cero: análisis + salida
 * (`standard_analysis`). `output` requiere un `analysis_run`, por eso `analyze`
 * va incluido — output+deliver solos serían un no-op.
 */
export const CASE_SCOPE_DEFAULT_TAIL: readonly string[] = [
  "analyze",
  "output",
  "deliver",
];
