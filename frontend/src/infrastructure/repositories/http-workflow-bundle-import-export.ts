import type { AxiosError, AxiosInstance } from "axios";

import type {
  BundleImportStrategy,
  WorkflowBundleEnvelope,
  WorkflowBundleImportReport,
  WorkflowTemplate,
} from "@/src/domain/entities/workflow-bundle-export";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { handleHttpError } from "@/src/utils/http-error-handler";

/**
 * E6 · W8 — bundle completo del workflow (doctypes + pipeline + reglas).
 *
 * Misma red que `http-workflow-rule-import-export.ts`: axios `authHttp`
 * (`baseURL:"/api"`) → proxy `src/proxy.ts` reescribe `/api/v1/*` al backend
 * con `X-Api-Key`. No requiere BFF route nueva (el proxy ya cumple la regla).
 *
 * El import manda `{ payload: envelope }` (el backend lee `request.payload`).
 */
export class HttpWorkflowBundleImportExportRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async export(
    workflowId: string,
  ): Promise<WorkflowBundleEnvelope | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowBundleEnvelope }>(
        `/v1/workflows/${workflowId}/export`,
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async preview(
    workflowId: string,
    envelope: WorkflowBundleEnvelope,
    strategy: BundleImportStrategy,
  ): Promise<WorkflowBundleImportReport | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowBundleImportReport }>(
        `/v1/workflows/${workflowId}/import/preview`,
        { payload: envelope },
        { params: { strategy } },
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async run(
    workflowId: string,
    envelope: WorkflowBundleEnvelope,
    strategy: BundleImportStrategy,
  ): Promise<WorkflowBundleImportReport | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowBundleImportReport }>(
        `/v1/workflows/${workflowId}/import`,
        { payload: envelope },
        { params: { strategy } },
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async templates(): Promise<WorkflowTemplate[] | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowTemplate[] }>(
        `/v1/workflow-templates`,
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
