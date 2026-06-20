export type WorkflowRuleCompilationStatus =
  | "PENDING"
  | "COMPILING"
  | "READY"
  | "FAILED"
  | "STALE";

export interface WorkflowRuleCompilation {
  uuid: string;
  ruleId: string;
  version: number;
  kind: string;
  status: WorkflowRuleCompilationStatus;
  artifact: Record<string, unknown> | null;
  compiledWith: Record<string, unknown> | null;
  error: string | null;
  createdAt: string | null;
  completedAt: string | null;
}
