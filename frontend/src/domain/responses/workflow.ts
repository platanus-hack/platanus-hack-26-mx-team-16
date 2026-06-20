import type { Workflow } from "@/src/domain/entities/workflow";

export interface WorkflowResponse {
  data: Workflow;
}

export interface WorkflowListResponse {
  data: Workflow[];
}
