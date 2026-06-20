/**
 * Mensajes en español para los códigos de error que el backend asigna al
 * campo ``error`` de un ``AnalysisRun``.
 *
 * Los códigos espejean los strings emitidos en
 * ``backend/src/workflows/infrastructure/services/analysis/runner.py`` y
 * ``backend/src/workflows/application/analysis_runs/runner_scheduler.py``.
 * Si el backend agrega un código nuevo y aún no está mapeado aquí, se
 * muestra el código crudo como fallback para no perder señal en debug.
 */

const ANALYSIS_RUN_ERROR_LABELS: Record<string, string> = {
  all_evaluations_errored: "Todas las reglas tuvieron error",
  no_classified_documents: "Ningún documento clasificado",
  orchestrator_crashed: "Falló el procesamiento",
};

export function formatAnalysisRunError(
  code: string | null | undefined
): string | null {
  if (!code) return null;
  return ANALYSIS_RUN_ERROR_LABELS[code] ?? code;
}
