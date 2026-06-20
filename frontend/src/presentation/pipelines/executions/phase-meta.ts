import type { PhaseExecutionStatus } from "@/src/domain/entities/workflow-phase-execution";
import type { WorkflowProcessingJobStatus } from "@/src/domain/events/processing-job-event";
import type { IconName } from "@/src/presentation/pipelines/spine/types";

/** Phase kind → the editor's node icon, so the run graph matches the canvas. */
const PHASE_KIND_ICON: Record<string, IconName> = {
  ingest: "ingest",
  extract_text: "extract_text",
  classify_pages: "classify_pages",
  extract_fields: "extract_fields",
  assess: "assess",
  validate_extraction: "validate_extraction",
  finalize: "finalize",
  extraction_gate: "extraction_gate",
  enrich: "enrich",
  analyze: "analyze",
  output: "output",
  deliver: "deliver",
  await_clarification: "await_clarification",
  human_review: "approval",
  await_documents: "await_documents",
};

export function phaseIcon(kind: string): IconName {
  return PHASE_KIND_ICON[kind] ?? "analyze";
}

/** Friendly Spanish labels for each recipe phase kind (PhaseKind values). */
export const PHASE_KIND_LABEL: Record<string, string> = {
  ingest: "Ingesta",
  extract_text: "Extracción de texto",
  classify_pages: "Clasificación",
  extract_fields: "Extracción de campos",
  assess: "Confianza (capa 2)",
  validate_extraction: "Validación",
  finalize: "Finalización",
  extraction_gate: "Compuerta de extracción",
  enrich: "Enriquecimiento",
  analyze: "Análisis",
  output: "Salida",
  deliver: "Entrega",
  await_clarification: "Espera de aclaración",
  human_review: "Revisión humana",
  await_documents: "Espera de documentos",
};

export function phaseLabel(kind: string): string {
  return PHASE_KIND_LABEL[kind] ?? kind;
}

export interface ToneClasses {
  /** Filled node on the rail / status dot. */
  node: string;
  /** Soft chip background + text + ring. */
  chip: string;
  /** Text color for inline status. */
  text: string;
}

export const PHASE_STATUS_TONE: Record<PhaseExecutionStatus, ToneClasses> = {
  COMPLETED: {
    node: "bg-success",
    chip: "bg-success/10 text-success-deep ring-success/25",
    text: "text-success-deep",
  },
  FAILED: {
    node: "bg-destructive",
    chip: "bg-destructive/10 text-destructive-deep ring-destructive/25",
    text: "text-destructive-deep",
  },
  RUNNING: {
    node: "bg-primary",
    chip: "bg-primary/10 text-primary ring-primary/25",
    text: "text-primary",
  },
  SKIPPED: {
    node: "bg-muted-foreground/40",
    chip: "bg-muted text-muted-foreground ring-border",
    text: "text-muted-foreground",
  },
};

export const PHASE_STATUS_LABEL: Record<PhaseExecutionStatus, string> = {
  COMPLETED: "completada",
  FAILED: "falló",
  RUNNING: "en curso",
  SKIPPED: "omitida",
};

/**
 * Box styling for the run graph — one node per executed phase, colored by
 * outcome: green when it ran, red when it errored (mirrors the editor canvas
 * card with a status tint).
 */
export const PHASE_FLOW_TONE: Record<
  PhaseExecutionStatus,
  { box: string; iconChip: string }
> = {
  COMPLETED: {
    box: "border-success/40",
    iconChip: "bg-success/10 text-success-deep",
  },
  FAILED: {
    box: "border-destructive/50 bg-destructive/5",
    iconChip: "bg-destructive/10 text-destructive-deep",
  },
  RUNNING: {
    box: "border-primary/40",
    iconChip: "bg-primary/10 text-primary",
  },
  SKIPPED: {
    box: "border-dashed border-border",
    iconChip: "bg-muted text-muted-foreground",
  },
};

export const JOB_STATUS_TONE: Record<WorkflowProcessingJobStatus, ToneClasses> =
  {
    COMPLETED: {
      node: "bg-success",
      chip: "bg-success/10 text-success-deep ring-success/25",
      text: "text-success-deep",
    },
    FAILED: {
      node: "bg-destructive",
      chip: "bg-destructive/10 text-destructive-deep ring-destructive/25",
      text: "text-destructive-deep",
    },
    PARTIAL: {
      node: "bg-warning",
      chip: "bg-warning/15 text-warning-deep ring-warning/30",
      text: "text-warning-deep",
    },
    PROCESSING: {
      node: "bg-primary",
      chip: "bg-primary/10 text-primary ring-primary/25",
      text: "text-primary",
    },
    RUNNING: {
      node: "bg-primary",
      chip: "bg-primary/10 text-primary ring-primary/25",
      text: "text-primary",
    },
    PENDING: {
      node: "bg-muted-foreground/40",
      chip: "bg-muted text-muted-foreground ring-border",
      text: "text-muted-foreground",
    },
  };

export const JOB_STATUS_LABEL: Record<WorkflowProcessingJobStatus, string> = {
  COMPLETED: "completada",
  FAILED: "falló",
  PARTIAL: "parcial",
  PROCESSING: "procesando",
  RUNNING: "en curso",
  PENDING: "en cola",
};

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} min ${rest} s`;
}
