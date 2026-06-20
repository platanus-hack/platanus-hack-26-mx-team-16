/**
 * Frontend registry for kind-specific UI overrides (spec §4.3, §13.4).
 * Kinds without an entry here use the generic schema-driven editor + JSON
 * tree result renderer. Add an entry when a kind needs a bespoke component
 * (e.g. SCORING with a slider gauge).
 */

import type { ComponentType } from "react";
import type { WorkflowRule } from "@/src/domain/entities/workflow-rule";
import type { WorkflowRuleResult } from "@/src/domain/entities/workflow-rule-result";

export interface WorkflowRuleConfigEditorProps {
  rule: Partial<WorkflowRule>;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export interface WorkflowRuleResultRendererProps {
  rule: WorkflowRule;
  result: WorkflowRuleResult;
}

export interface WorkflowRuleKindUI {
  configEditor?: ComponentType<WorkflowRuleConfigEditorProps>;
  resultRenderer?: ComponentType<WorkflowRuleResultRendererProps>;
}

const REGISTRY: Record<string, WorkflowRuleKindUI> = {};

export function registerWorkflowRuleKindUI(name: string, ui: WorkflowRuleKindUI): void {
  REGISTRY[name] = { ...REGISTRY[name], ...ui };
}

export function getWorkflowRuleKindUI(name: string): WorkflowRuleKindUI | undefined {
  return REGISTRY[name];
}
