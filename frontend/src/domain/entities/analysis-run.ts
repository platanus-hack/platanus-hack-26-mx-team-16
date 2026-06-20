export type AnalysisRunStatus =
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELING"
  | "CANCELED";

export type AnalysisRunTrigger = "USER" | "RETRY" | "SCHEDULED" | "SYSTEM";

export interface AnalysisRunModelConfig {
  id?: string;
  [key: string]: unknown;
}

export interface AnalysisRun {
  uuid: string;
  tenantId: string;
  workflowId: string;
  workflowCaseId: string;
  status: AnalysisRunStatus;
  trigger: AnalysisRunTrigger;
  triggeredBy: string | null;
  startedAt: string | null;
  completedAt: string | null;
  canceledAt: string | null;
  canceledBy: string | null;
  error: string | null;
  reviewerModel: AnalysisRunModelConfig | null;
  criticModel: AnalysisRunModelConfig | null;
  consensusSamples: number | null;
  rulesTotal: number | null;
  rulesPassed: number | null;
  rulesFailed: number | null;
  rulesInconclusive: number | null;
  durationMs: number | null;
  createdAt: string | null;
}

export interface Citation {
  value: string | number | boolean | null;
  fieldPath: string | null;
  documentId: string | null;
  documentTypeSlug: string | null;
  subCheckId: string | null;
}

export interface ConsensusInfo {
  nSamples: number | null;
  agreementRatio: number | null;
  verdicts: Array<boolean | null>;
}

/**
 * Each rule result references one or more case documents by their doctype
 * slug. The backend resolves the human-readable doctype name in
 * `documentTypeName` so the UI doesn't have to walk the case tree.
 */
export interface DocumentRef {
  documentId: string | null;
  documentTypeName: string | null;
}

export interface AnalysisRuleResult {
  uuid: string;
  analysisRunId: string;
  caseId: string;
  ruleId: string;
  ruleName: string | null;
  ruleContent: string | null;
  isPassed: boolean | null;
  reasoning: string | null;
  renderedPrompt: string | null;
  documentRefs: Record<string, DocumentRef>;
  citations: Citation[];
  preliminaryChecks: Record<string, unknown>;
  consensus: ConsensusInfo;
  criticFeedback: string | null;
  criticIterations: number;
  verificationWarnings: string[];
  unresolvedTokens: string[];
  structuredOutput: Record<string, unknown> | null;
  error: string | null;
  createdAt: string | null;
}

export interface AnalysisRunDetail extends AnalysisRun {
  results: AnalysisRuleResult[];
}

// ─── SSE event payloads (spec §7.1) ────────────────────────────────────────

export type AnalysisRunEventType =
  | "RUN_STARTED"
  | "EVALUATION_STARTED"
  | "STAGE_PROGRESS"
  | "RULE_RESULT_READY"
  | "RUN_PROGRESS"
  | "RUN_COMPLETED"
  | "RUN_FAILED"
  | "RUN_CANCELED";

interface BaseEvent<T extends AnalysisRunEventType, P> {
  type: T;
  seq: number;
  ts: string;
  run_id: string;
  payload: P;
}

export type AnalysisRunEvent =
  | BaseEvent<"RUN_STARTED", { runId: string; totalEvaluations: number }>
  | BaseEvent<"EVALUATION_STARTED", { ruleId: string; combinationKey: string }>
  | BaseEvent<
      "STAGE_PROGRESS",
      {
        ruleId: string;
        combinationKey: string;
        stage: 1 | 2 | 3 | 4 | 5;
        status: string;
      }
    >
  | BaseEvent<"RULE_RESULT_READY", AnalysisRuleResult>
  | BaseEvent<"RUN_PROGRESS", { completed: number; total: number }>
  | BaseEvent<
      "RUN_COMPLETED",
      {
        runId: string;
        summary: { passed: number; failed: number; errored: number };
      }
    >
  | BaseEvent<"RUN_FAILED", { runId: string; error: string }>
  | BaseEvent<"RUN_CANCELED", { runId: string; reason: string }>;

export type ConfidenceLevel =
  | "high"
  | "medium"
  | "critic_reviewed"
  | "inconclusive"
  | "unknown";

export function classifyConfidence(
  result: AnalysisRuleResult
): ConfidenceLevel {
  if ((result.criticIterations ?? 0) > 0) return "critic_reviewed";
  if (result.error === "no_consensus") return "inconclusive";
  const ratio = result.consensus?.agreementRatio ?? null;
  if (ratio === null) return "unknown";
  if (ratio === 1.0) return "high";
  if (ratio >= 0.6 && ratio < 1.0) return "medium";
  return "inconclusive";
}
