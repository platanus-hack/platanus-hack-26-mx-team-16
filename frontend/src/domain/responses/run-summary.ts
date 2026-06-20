import type {
  RunSummary,
  WorkflowSynthesisConfig,
} from "@/src/domain/entities/run-summary";

export interface RunSummaryResponse {
  data: RunSummary;
  datetime: string;
}

export interface WorkflowSynthesisConfigResponse {
  data: WorkflowSynthesisConfig;
  datetime: string;
}
