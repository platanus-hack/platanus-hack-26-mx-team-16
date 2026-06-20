import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  RunSummaryResponse,
  WorkflowSynthesisConfigResponse,
} from "@/src/domain/responses/run-summary";

export interface UpdateSynthesisConfigPayload {
  output_schema?: Record<string, unknown> | null;
  synthesis_template?: string | null;
  synthesis_enabled?: boolean;
}

export interface RunSummaryRepository {
  getByRunId(runId: string): Promise<RunSummaryResponse | ErrorFeeback>;
  resynthesize(
    runId: string,
    force?: boolean
  ): Promise<RunSummaryResponse | ErrorFeeback>;
  getWorkflowConfig(
    workflowId: string
  ): Promise<WorkflowSynthesisConfigResponse | ErrorFeeback>;
  updateWorkflowConfig(
    workflowId: string,
    payload: UpdateSynthesisConfigPayload
  ): Promise<WorkflowSynthesisConfigResponse | ErrorFeeback>;
}
