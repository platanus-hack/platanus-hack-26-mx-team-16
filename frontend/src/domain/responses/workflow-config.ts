import type { WorkflowConfig } from "@/src/domain/entities/workflow-config";

export interface WorkflowConfigResponse {
  data: WorkflowConfig;
  datetime: string;
}
