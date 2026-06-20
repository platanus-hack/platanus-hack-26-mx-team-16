import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { WorkflowConfigResponse } from "@/src/domain/responses/workflow-config";

export interface WorkflowConfigRepository {
  getByWorkflowUuid(
    workflowUuid: string
  ): Promise<WorkflowConfigResponse | ErrorFeeback>;
}
