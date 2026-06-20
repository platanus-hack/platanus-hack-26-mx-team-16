/**
 * Domain entities for the redesigned workflow rules system (spec §3).
 * Names use the WorkflowRule* prefix; file is short for ergonomic imports.
 */

export type WorkflowRuleScopeMode =
  | "SINGLE_DOCUMENT"
  | "TUPLE_CARTESIAN"
  | "AGGREGATE_OVER_TYPE"
  | "ALL_DOCUMENTS";

export type WorkflowRuleOnEmpty = "SKIPPED" | "FAILED" | "PASSED";

export interface WorkflowRuleScope {
  mode: WorkflowRuleScopeMode;
  documentType?: string | null;
  documentTypes?: string[] | null;
  onEmpty: WorkflowRuleOnEmpty;
}

export interface WorkflowRule {
  uuid: string;
  tenantId: string;
  workflowId: string;
  name: string;
  position: number;
  isActive: boolean;
  kind: string;
  prompt: string;
  config: Record<string, unknown>;
  scope: WorkflowRuleScope;
  knowledgeRefs: string[];
  currentCompilationId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface CreateWorkflowRulePayload {
  name: string;
  kind: string;
  prompt: string;
  config?: Record<string, unknown>;
  scope?: WorkflowRuleScope;
  knowledgeRefs?: string[];
  isActive?: boolean;
}

export interface UpdateWorkflowRulePayload {
  name?: string;
  kind?: string;
  prompt?: string;
  config?: Record<string, unknown>;
  scope?: WorkflowRuleScope;
  knowledgeRefs?: string[];
  isActive?: boolean;
}
