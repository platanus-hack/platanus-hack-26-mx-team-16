/** Export envelope (spec §14.2). */
export interface WorkflowRuleExportEnvelope {
  schemaVersion: string;
  exportedAt: string;
  sourceWorkflowId: string;
  sourceTenantId: string;
  rules: WorkflowRuleExportEntry[];
}

export interface WorkflowRuleExportEntry {
  name: string;
  kind: string;
  prompt: string;
  config: Record<string, unknown>;
  scope: Record<string, unknown>;
  knowledgeRefsExternal: Array<{ name: string }>;
  position: number;
  isActive: boolean;
}

export type ImportConflictStrategy = "SKIP" | "OVERWRITE" | "RENAME" | "FAIL";

export interface WorkflowRuleImportReport {
  created: number;
  overwritten: number;
  skipped: number;
  renamed: number;
  failed: number;
  errors: string[];
  unresolvedKbRefs: string[];
  unresolvedDocTypeSlugs: string[];
}
