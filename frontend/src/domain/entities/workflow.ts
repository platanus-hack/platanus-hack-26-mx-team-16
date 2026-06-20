// E7 · F2: `WorkflowType` (STANDARD|ANALYSIS) murió — un solo tipo de workflow
// cuyas capacidades deriva su pipeline.

// E7 · F0: capacidades derivadas del pipeline vigente (backend `derive_capabilities`).
// Reemplazan a `workflowType` para gatear tabs/acciones del workflow; los valores
// son el contrato snake_case que envía el backend en `capabilities`.
export type WorkflowCapability =
  | "extraction"
  | "multi_doc_dossier"
  | "analysis"
  | "layer2_confidence"
  | "enrichment"
  | "clarification"
  | "human_review"
  | "structured_output"
  | "fan_out"
  | "qa";

export interface CaseNounForms {
  one: string;
  other: string;
}

/**
 * Sustantivo visible del caso por workflow (es/en · one/other). null/ausente ⇒
 * la UI usa el default i18n («Caso/Casos», "Case/Cases"). El nombre técnico
 * `case` no cambia (product/specs/data-model/case-noun.md).
 */
export interface CaseNoun {
  es: CaseNounForms;
  en: CaseNounForms;
}

export interface Workflow {
  uuid: string;
  name: string;
  // Opcional: presente en respuestas del backend; ausente en mocks/legacy.
  capabilities?: WorkflowCapability[];
  selectedDocTypes: string[];
  structuringModel: string | null;
  llmModel: string | null;
  webhookUrl: string | null;
  webhookEnabled: boolean;
  webhookEvents: string[];
  // Sustantivo visible del caso, configurable por workflow. null/ausente ⇒
  // default i18n (ver helper `caseNoun`).
  caseNoun?: CaseNoun | null;
  createdAt: string | null;
  updatedAt: string | null;
}

/** ¿El workflow expone una capacidad derivada de su pipeline? (E7 · F0) */
export function hasCapability(
  workflow: Pick<Workflow, "capabilities"> | null | undefined,
  capability: WorkflowCapability
): boolean {
  return workflow?.capabilities?.includes(capability) ?? false;
}

/**
 * cases-table-upload · F2/D3: el nombre del caso es editable solo en workflows
 * dossier (capability `multi_doc_dossier`, derivada de la fase `await_documents`).
 * En per_upload el nombre lo fija el archivo (read-only).
 *
 * ⚠️ Gatear sobre un workflow CARGADO: con `workflow` null/undefined (loading o
 * error) cae a `false`; el caller debe deshabilitar el CTA mientras carga en vez
 * de tratar el workflow como per_upload (ver F5).
 */
export function caseNameEditable(
  workflow: Pick<Workflow, "capabilities"> | null | undefined
): boolean {
  return hasCapability(workflow, "multi_doc_dossier");
}
