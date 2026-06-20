/**
 * Workflow bundle export/import (E6 · W8 · diseño §4).
 *
 * Espejo del envelope/report camelCase del backend
 * (`backend/src/workflows/application/workflows/import_export/`):
 * - Export: `GET /v1/workflows/{id}/export` → envelope schemaVersion 1.0.
 * - Import: `POST /v1/workflows/{id}/import[/preview]?strategy=` con body
 *   `{ payload: { ...envelope } }` → report nested por sección.
 *
 * El envelope es opaco para el FE: se descarga tal cual y se re-sube tal cual
 * (la plantilla del catálogo viaja en el mismo shape).
 */
export type WorkflowBundleEnvelope = Record<string, unknown>;

/** Mismas estrategias del importer de reglas (backend `ImportConflictStrategy`). */
export type BundleImportStrategy = "skip" | "overwrite" | "rename" | "fail";

export interface WorkflowBundleImportReport {
  dryRun: boolean;
  documentTypes: {
    created: number;
    overwritten: number;
    skipped: number;
    failed: number;
  };
  pipeline: {
    slug: string | null;
    version: number | null;
    created: boolean;
    bound: boolean;
  };
  rules: {
    created: number;
    overwritten: number;
    skipped: number;
    renamed: number;
    failed: number;
  };
  recompilationScheduled: number;
  unresolvedKbRefs: string[];
  unresolvedDocTypeSlugs: string[];
  errors: string[];
}

/** Item del catálogo de plantillas (`GET /v1/workflow-templates`). */
export interface WorkflowTemplate {
  slug: string;
  name: string;
  description: string | null;
  industry: string | null;
  envelope: WorkflowBundleEnvelope;
}
