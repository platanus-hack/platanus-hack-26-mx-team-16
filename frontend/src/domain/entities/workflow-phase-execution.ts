/**
 * Mirror of the backend WorkflowPhaseExecution presenter (camelCased by the
 * response middleware). One row per recipe phase run inside an execution
 * (a processing job) — powers the "Ejecuciones" Step-Functions detail.
 */

export type PhaseExecutionStatus =
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED";

export interface WorkflowPhaseExecution {
  uuid: string;
  processingJobId: string;
  seq: number;
  phaseId: string;
  phaseKind: string;
  status: PhaseExecutionStatus;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  /** Compact JSON of the artifact the phase produced ({ key, value } | { truncated }). */
  outputSnapshot: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  createdAt: string | null;
}
