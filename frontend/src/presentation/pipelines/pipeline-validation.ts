import type {
  PhaseCatalogEntry,
  PipelinePhase,
} from "@/src/application/hooks/queries/pipelines";

/**
 * Validación client-side espejo de la autoritativa del backend
 * (`pipeline_validation.validate_phases`). El 422 del publish/dry-run sigue
 * siendo la fuente de verdad; esto es feedback rápido para bloquear drops
 * inválidos y marcar tarjetas antes de pegarle al backend.
 */

// Invariante estructural E4 (validate_phases): todas las fases document-scope
// van ANTES de la primera case-scope; si hay await_documents, es la PRIMERA
// case-scope. fan_out* solo en classify_pages (lo valida el backend; aquí solo
// el orden de scope que afecta al drag&drop).
export interface RecipeStructuralIssue {
  phaseId: string;
  message: string;
}

export function scopeOf(
  kind: string,
  catalog: PhaseCatalogEntry[],
): "document" | "case" {
  return catalog.find((e) => e.kind === kind)?.scope ?? "document";
}

export function validateRecipeStructure(
  phases: PipelinePhase[],
  catalog: PhaseCatalogEntry[],
): RecipeStructuralIssue[] {
  const issues: RecipeStructuralIssue[] = [];
  let seenCase = false;
  let firstCaseIndex = -1;

  phases.forEach((phase, i) => {
    const scope = scopeOf(phase.kind, catalog);
    if (scope === "case") {
      if (firstCaseIndex === -1) firstCaseIndex = i;
      seenCase = true;
    } else if (seenCase) {
      issues.push({
        phaseId: phase.id,
        message:
          "Una fase de documento no puede ir después de una fase de caso.",
      });
    }
  });

  // await_documents debe ser la primera fase case-scope.
  const awaitIdx = phases.findIndex((p) => p.kind === "await_documents");
  if (awaitIdx !== -1 && awaitIdx !== firstCaseIndex) {
    issues.push({
      phaseId: phases[awaitIdx].id,
      message: "await_documents debe ser la primera fase de caso.",
    });
  }

  return issues;
}

/**
 * ¿Es válido soltar `phase` (que se está arrastrando) en la posición `toIndex`
 * de `phases` (ya reordenada)? Reusa validateRecipeStructure sobre el resultado
 * tentativo para bloquear drops que rompan el invariante de scope.
 */
export function isOrderingValid(
  phases: PipelinePhase[],
  catalog: PhaseCatalogEntry[],
): boolean {
  return validateRecipeStructure(phases, catalog).length === 0;
}
