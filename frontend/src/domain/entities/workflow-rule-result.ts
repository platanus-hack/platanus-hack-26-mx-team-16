export type WorkflowRuleResultStatus = "SUCCESS" | "FAILED" | "ERRORED" | "SKIPPED";

export interface WorkflowRuleResult {
  uuid: string;
  tenantId: string;
  workflowAnalysisRunId: string;
  ruleId: string;
  caseId: string;
  kind: string;
  status: WorkflowRuleResultStatus;
  output: Record<string, unknown> | null;
  reasoning: string | null;
  citations: Array<Record<string, unknown>>;
  documentRefs: Record<string, unknown>;
  documentRefsHash: string;
  renderedPrompt: string | null;
  evaluationMetadata: Record<string, unknown>;
  error: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
