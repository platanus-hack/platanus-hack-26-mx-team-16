// adapter.ts — bridge entre los datos reales del pipeline (lista plana de
// `PipelinePhase` + catálogo del backend) y el modelo del editor
// visual (`Stage[]` + `PipelineState`).
//
//   forward  buildSpine(phases, catalog, ...)  → { stages, state }  (render)
//   inverse  buildDraft(state, current, ...)   → { phases }         (onChange)
//
// El editor es "headless de datos": esto es lo único que sabe del dominio Doxiq.
// La edición de config NO pasa por aquí (la hace PhaseDrawer sobre el store);
// el spine solo maneja ESTRUCTURA (etapas, orden, opcionales).
import type {
  PhaseCatalogEntry,
  PipelinePhase,
} from "@/src/application/hooks/queries/pipelines";
import { makePhaseId } from "@/src/application/stores/pipeline-editor-store";
import { stageIdForPhase } from "@/src/presentation/pipelines/pipeline-stages";

import type {
  AccentName,
  IconName,
  Phase,
  PipelineState,
  Stage,
  StageLayout,
  StageType,
} from "./types";

/**
 * Plantilla de una fase dentro de una etapa. `editorKind` es la identidad en la
 * UI (única por etapa); el motor usa `engineKind` (p. ej. `approval` → el
 * `human_review` de la cola de aprobación).
 */
interface PhaseTemplate {
  editorKind: string;
  label: string;
  summary: string;
  optional?: boolean;
  branch?: boolean;
  sameKind?: string;
}

interface SpineStageDef {
  id: string;
  num: string;
  name: string;
  baseType: StageType;
  scope: "document" | "case";
  accent: AccentName;
  tag: string;
  layout: StageLayout;
  summary: string;
  removable: boolean;
  toggleable?: boolean;
  atomic?: boolean;
  icon: IconName;
  templates: PhaseTemplate[];
}

// editorKind → engine kind (lo demás es identidad).
const ENGINE_KIND: Record<string, string> = {
  approval: "human_review",
};
function engineKindOf(editorKind: string): string {
  return ENGINE_KIND[editorKind] ?? editorKind;
}

// Config extra que define el rol del kind compartido (espejo de capability_macros).
const TEMPLATE_CONFIG: Record<string, Record<string, unknown>> = {
  approval: { kind: "approval" },
};

/** Fase real → su editorKind (inverso de ENGINE_KIND, vía la etapa dueña). */
function realEditorKind(phase: PipelinePhase): string {
  if (phase.kind === "human_review") return "approval";
  return phase.kind;
}

// Catálogo estático de las 7 etapas (ids = STAGE_DEFS del proyecto). Mismo
// modelo mental que `pipeline-stages.ts` / `case-capabilities.ts`, con los
// metadatos visuales del editor (acento, icono, layout).
const SPINE_STAGES: readonly SpineStageDef[] = [
  {
    id: "extraction",
    num: "1",
    name: "Extracción",
    baseType: "group",
    scope: "document",
    accent: "teal",
    tag: "Grupo · cadena de dependencia",
    layout: "stack",
    summary:
      "Procesa cada archivo y extrae sus campos. Al terminar emite `document.extracted`.",
    removable: false,
    icon: "classify_pages",
    templates: [
      {
        editorKind: "ingest",
        label: "Ingesta",
        summary: "Recibe el archivo y normaliza el formato de entrada.",
      },
      {
        editorKind: "extract_text",
        label: "Extraer texto (OCR)",
        summary: "OCR y extracción de la capa de texto del documento.",
      },
      {
        editorKind: "classify_pages",
        label: "Clasificar páginas",
        summary: "Asigna un tipo de documento a cada página.",
      },
      {
        editorKind: "extract_fields",
        label: "Extraer campos",
        summary: "Extrae los campos estructurados según el esquema del tipo.",
      },
      {
        editorKind: "assess",
        label: "Confianza capa-2",
        summary: "Evalúa la calidad de la extracción antes de continuar.",
        optional: true,
      },
      {
        editorKind: "validate_extraction",
        label: "Validar extracción",
        summary: "Aplica reglas de validación sobre los campos extraídos.",
        optional: true,
      },
      {
        editorKind: "finalize",
        label: "Finalizar",
        summary:
          "Cierra el documento si es straight-through (sin pasos de caso).",
      },
    ],
  },
  {
    id: "completeness",
    num: "2",
    name: "Completitud",
    baseType: "solo",
    scope: "case",
    accent: "amber",
    tag: "Fase suelta · primera del caso",
    layout: "stack",
    summary:
      "Primera fase del caso: convierte el caso en expediente y espera los documentos.",
    removable: true,
    icon: "await_documents",
    templates: [
      {
        editorKind: "await_documents",
        label: "Esperar documentos",
        summary: "Retiene el caso hasta reunir los documentos requeridos.",
      },
    ],
  },
  {
    id: "quality",
    num: "3",
    name: "Control de calidad",
    baseType: "group",
    scope: "case",
    accent: "gold",
    tag: "Grupo · compuerta + pausa opcional",
    layout: "stack",
    summary:
      "Evalúa la confianza de la extracción y, ante baja confianza, pide aclaración o manda a revisión.",
    removable: true,
    toggleable: true,
    icon: "extraction_gate",
    templates: [
      {
        editorKind: "extraction_gate",
        label: "Compuerta de extracción",
        summary:
          "Evalúa la confianza por campo y enruta a aclaración o revisión según la policy.",
      },
      {
        editorKind: "await_clarification",
        label: "Aclaración (pausa durable)",
        summary:
          "Pausa incondicional esperando datos de un humano/sistema (sin gate de confianza).",
        optional: true,
      },
    ],
  },
  {
    id: "enrichment",
    num: "4",
    name: "Enriquecimiento",
    baseType: "solo",
    scope: "case",
    accent: "violet",
    tag: "Fase suelta · independiente",
    layout: "stack",
    summary:
      "Llama herramientas HTTP firmadas y persiste el resultado en el caso.",
    removable: true,
    icon: "enrich",
    templates: [
      {
        editorKind: "enrich",
        label: "Enriquecimiento",
        summary:
          "Ejecuta una herramienta HTTP firmada contra un servicio externo.",
      },
    ],
  },
  {
    id: "analysis",
    num: "5",
    name: "Análisis",
    baseType: "solo",
    scope: "case",
    accent: "blue",
    tag: "Fase suelta · independiente",
    layout: "stack",
    summary:
      "Evalúa las reglas de negocio sobre los datos consolidados del caso.",
    removable: true,
    icon: "analyze",
    templates: [
      {
        editorKind: "analyze",
        label: "Análisis",
        summary: "Aplica el motor de reglas de negocio y produce un veredicto.",
      },
    ],
  },
  {
    id: "approval",
    num: "6",
    name: "Aprobación",
    baseType: "solo",
    scope: "case",
    accent: "rose",
    tag: "Fase suelta · independiente",
    layout: "stack",
    summary:
      "Cola de aprobación humana final (mismo kind human_review, sin trigger gate).",
    removable: true,
    icon: "approval",
    templates: [
      {
        editorKind: "approval",
        label: "Aprobación",
        summary: "Aprobación humana final antes de entregar.",
        sameKind: "human_review",
      },
    ],
  },
  {
    id: "output",
    num: "7",
    name: "Salida",
    baseType: "group",
    scope: "case",
    accent: "teal",
    tag: "Grupo · par atómico",
    layout: "stack",
    summary:
      "Par atómico: output proyecta el resultado y deliver lo entrega y cierra el caso.",
    removable: false,
    atomic: true,
    icon: "deliver",
    templates: [
      {
        editorKind: "output",
        label: "Construir salida",
        summary: "Proyecta y sintetiza el resultado final del caso.",
      },
      {
        editorKind: "deliver",
        label: "Entregar",
        summary: "Entrega el resultado (`case.output.ready`) y cierra el caso.",
      },
    ],
  },
];

const SPINE_BY_ID = new Map(SPINE_STAGES.map((s) => [s.id, s]));

/** Etapas removibles → addable en el menú "+". */
export const SPINE_ADDABLE: readonly string[] = SPINE_STAGES.filter(
  (s) => s.removable
).map((s) => s.id);

function catalogDefaults(
  catalog: PhaseCatalogEntry[],
  kind: string
): Record<string, unknown> {
  const entry = catalog.find((e) => e.kind === kind);
  const cfg: Record<string, unknown> = {};
  if (entry) {
    for (const [k, field] of Object.entries(entry.configSchema)) {
      if (field.default !== undefined) cfg[k] = field.default;
    }
  }
  return cfg;
}

// ── forward: datos reales → modelo del editor ────────────────────────────────

export function buildSpine(phases: PipelinePhase[]): {
  stages: Stage[];
  state: PipelineState;
  addable: string[];
} {
  // Agrupa fases reales por etapa y editorKind (preserva el orden / multi-enrich).
  const byStage = new Map<string, PipelinePhase[]>();
  for (const p of phases) {
    const sid = stageIdForPhase(p);
    const bucket = byStage.get(sid);
    if (bucket) bucket.push(p);
    else byStage.set(sid, [p]);
  }

  const stages: Stage[] = SPINE_STAGES.map((def, rank) => {
    const reals = byStage.get(def.id) ?? [];
    const phaseEls: Phase[] = [];
    for (const tmpl of def.templates) {
      const matches = reals.filter(
        (p) => realEditorKind(p) === tmpl.editorKind
      );
      if (matches.length) {
        for (const real of matches) {
          phaseEls.push(makePhase(def, tmpl, real));
        }
      } else {
        phaseEls.push(makePhase(def, tmpl, null));
      }
    }
    // Una etapa "solo" con varias instancias reales (multi-enrich) se muestra
    // como grupo para que se vean todas las fases.
    const type: StageType =
      def.baseType === "solo" && phaseEls.length > 1 ? "group" : def.baseType;
    return {
      id: def.id,
      num: def.num,
      rank,
      name: def.name,
      type,
      scope: def.scope,
      accent: def.accent,
      tag: def.tag,
      layout: def.layout,
      summary: def.summary,
      removable: def.removable,
      toggleable: def.toggleable,
      atomic: def.atomic,
      icon: def.icon,
      phases: phaseEls,
    };
  });

  // order: etapas activas (con ≥1 fase real) en orden de aparición de las fases.
  const order: string[] = [];
  const seen = new Set<string>();
  for (const p of phases) {
    const sid = stageIdForPhase(p);
    if (!seen.has(sid)) {
      seen.add(sid);
      order.push(sid);
    }
  }

  // optional: presencia real de cada fase opcional.
  const optional: Record<string, boolean> = {};
  for (const def of SPINE_STAGES) {
    const reals = byStage.get(def.id) ?? [];
    for (const tmpl of def.templates) {
      if (!tmpl.optional) continue;
      optional[tmpl.editorKind] = reals.some(
        (p) => realEditorKind(p) === tmpl.editorKind
      );
    }
  }

  return {
    stages,
    state: { order, collapsed: {}, optional, config: {} },
    addable: [...SPINE_ADDABLE],
  };
}

function makePhase(
  def: SpineStageDef,
  tmpl: PhaseTemplate,
  real: PipelinePhase | null
): Phase {
  return {
    kind: tmpl.editorKind,
    label: tmpl.label,
    icon: tmpl.editorKind as IconName,
    scope: def.scope,
    summary: tmpl.summary,
    realId: real?.id,
    optional: tmpl.optional,
    branch: tmpl.branch,
    sameKind: tmpl.sameKind,
    config: [],
  };
}

// ── inverse: modelo del editor → lista plana de fases ────────────────────────

export function buildDraft(
  state: PipelineState,
  current: PipelinePhase[],
  catalog: PhaseCatalogEntry[]
): { phases: PipelinePhase[] } {
  const out: PipelinePhase[] = [];
  for (const stageId of state.order) {
    const def = SPINE_BY_ID.get(stageId);
    if (!def) continue;
    for (const tmpl of def.templates) {
      if (tmpl.optional && state.optional[tmpl.editorKind] === false) continue;
      // Reutiliza las fases reales existentes (preserva id/config y el N de
      // enrich); solo instancia con defaults las recién activadas.
      const existing = current.filter(
        (p) =>
          stageIdForPhase(p) === stageId &&
          realEditorKind(p) === tmpl.editorKind
      );
      if (existing.length) out.push(...existing);
      else out.push(instantiate(tmpl, out, catalog));
    }
  }

  // Las policies van plegadas en config de fase (completitud → await_documents.config,
  // activación → extraction_gate.config.activation, D-A): el loop de arriba ya preserva
  // esa config, así que no hay scaffold version-level que aplicar. El scaffold de stages
  // al agregar capacidades vive en el macro backend (apply_capability).
  return { phases: out };
}

function instantiate(
  tmpl: PhaseTemplate,
  existing: PipelinePhase[],
  catalog: PhaseCatalogEntry[]
): PipelinePhase {
  const kind = engineKindOf(tmpl.editorKind);
  return {
    id: makePhaseId(kind, existing),
    kind,
    config: {
      ...catalogDefaults(catalog, kind),
      ...(TEMPLATE_CONFIG[tmpl.editorKind] ?? {}),
    },
  };
}
