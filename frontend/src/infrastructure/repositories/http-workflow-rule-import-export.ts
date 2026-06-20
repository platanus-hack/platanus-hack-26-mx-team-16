import type { AxiosError, AxiosInstance } from "axios";
import type {
  ImportConflictStrategy,
  WorkflowRuleExportEnvelope,
  WorkflowRuleImportReport,
} from "@/src/domain/entities/workflow-rule-export";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { handleHttpError } from "@/src/utils/http-error-handler";

export class HttpWorkflowRuleImportExportRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async export(
    workflowId: string,
  ): Promise<WorkflowRuleExportEnvelope | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRuleExportEnvelope }>(
        `/v1/workflows/${workflowId}/workflow-rules/export`,
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async preview(
    workflowId: string,
    payload: WorkflowRuleExportEnvelope,
  ): Promise<WorkflowRuleImportReport | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowRuleImportReport }>(
        `/v1/workflows/${workflowId}/workflow-rules/import/preview`,
        { payload },
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async run(
    workflowId: string,
    payload: WorkflowRuleExportEnvelope,
    strategy: ImportConflictStrategy,
  ): Promise<WorkflowRuleImportReport | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowRuleImportReport }>(
        `/v1/workflows/${workflowId}/workflow-rules/import`,
        { payload },
        { params: { strategy } },
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
