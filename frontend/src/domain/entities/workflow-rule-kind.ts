/** Plugin descriptor returned by GET /workflow-rules/kinds (spec §4.3). */
export interface WorkflowRuleKindDescriptor {
  name: string;
  label: string;
  description: string;
  configSchema: Record<string, unknown>;
  defaultConfig: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
}
