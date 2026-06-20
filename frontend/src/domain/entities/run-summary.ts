export type Verdict = "PASS" | "FAIL" | "REVIEW";

export type NarrativeStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED";

export interface SummarySignal {
  ruleId: string;
  kind: string;
  severity: string;
  polarity: string;
  weight: number;
  detail: Record<string, unknown>;
}

export interface RunSummary {
  uuid: string;
  workflowAnalysisRunId: string;
  tenantId: string;
  verdict: Verdict;
  signals: SummarySignal[];
  signalsByPolarity: Record<string, number>;
  signalsBySeverity: Record<string, number>;
  confidenceScore: number | null;
  blockingFailures: string[];
  degradedRules: string[];
  output: Record<string, unknown> | null;
  outputSchemaSnapshot: Record<string, unknown> | null;
  synthesisTemplateSnapshot: string | null;
  narrativeStatus: NarrativeStatus;
  narrativeError: string | null;
  model: string | null;
  provider: string | null;
  inputHash: string;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface WorkflowSynthesisConfig {
  outputSchema: Record<string, unknown> | null;
  synthesisTemplate: string | null;
  synthesisEnabled: boolean;
}

export type RunSummaryEventType =
  | "summary.verdict_ready"
  | "summary.narrative_started"
  | "summary.narrative_completed"
  | "summary.failed";

export interface RunSummaryEvent {
  type: RunSummaryEventType;
  runId: string;
  payload: Record<string, unknown>;
}
