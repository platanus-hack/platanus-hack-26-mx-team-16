/**
 * First-party UI overrides for built-in rule kinds.
 *
 * Imported by ``WorkflowRuleModal`` so the registration runs the first time
 * the modal mounts — which is the only place the overrides are consumed.
 * Add additional kinds here as the registry grows.
 */

import { registerWorkflowRuleKindUI } from "@/src/application/lib/workflow-rule-kinds";
import { DerivationConfigEditor } from "@/src/presentation/components/workflow-rule-derivation-editor";

let registered = false;

export function registerDefaultWorkflowRuleKindUIs(): void {
  if (registered) return;
  registered = true;
  registerWorkflowRuleKindUI("DERIVATION", { configEditor: DerivationConfigEditor });
}
