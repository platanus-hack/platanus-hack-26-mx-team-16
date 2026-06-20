import type { AxiosError, AxiosInstance } from "axios";
import type {
  CreateWorkflowRulePayload,
  UpdateWorkflowRulePayload,
  WorkflowRule,
} from "@/src/domain/entities/workflow-rule";
import type { WorkflowRuleCompilation } from "@/src/domain/entities/workflow-rule-compilation";
import type { WorkflowRuleKindDescriptor } from "@/src/domain/entities/workflow-rule-kind";
import type { WorkflowRuleResult } from "@/src/domain/entities/workflow-rule-result";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import { handleHttpError } from "@/src/utils/http-error-handler";

interface Envelope<T> {
  data: T;
  datetime: string;
}

function ok<T>(data: T): Envelope<T> {
  return { data, datetime: new Date().toISOString() };
}

export class HttpWorkflowRuleRepository {
  constructor(private readonly httpClient: AxiosInstance) {}

  async listKinds(): Promise<Envelope<WorkflowRuleKindDescriptor[]> | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRuleKindDescriptor[] }>(
        "/v1/workflow-rules/kinds",
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async list(workflowId: string): Promise<Envelope<WorkflowRule[]> | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRule[] }>(
        `/v1/workflows/${workflowId}/workflow-rules`,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async get(ruleId: string): Promise<Envelope<WorkflowRule> | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRule }>(
        `/v1/workflow-rules/${ruleId}`,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async create(
    workflowId: string,
    payload: CreateWorkflowRulePayload,
  ): Promise<Envelope<WorkflowRule> | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowRule }>(
        `/v1/workflows/${workflowId}/workflow-rules`,
        payload,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async update(
    ruleId: string,
    payload: UpdateWorkflowRulePayload,
  ): Promise<Envelope<WorkflowRule> | ErrorFeeback> {
    try {
      const response = await this.httpClient.put<{ data: WorkflowRule }>(
        `/v1/workflow-rules/${ruleId}`,
        payload,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async delete(ruleId: string): Promise<{ status: "ok" } | ErrorFeeback> {
    try {
      await this.httpClient.delete(`/v1/workflow-rules/${ruleId}`);
      return { status: "ok" };
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async reorder(
    workflowId: string,
    ruleIds: string[],
  ): Promise<Envelope<WorkflowRule[]> | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: WorkflowRule[] }>(
        `/v1/workflows/${workflowId}/workflow-rules/reorder`,
        { ruleIds },
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async recompile(ruleId: string): Promise<{ status: string } | ErrorFeeback> {
    try {
      const response = await this.httpClient.post<{ data: { status: string } }>(
        `/v1/workflow-rules/${ruleId}/recompile`,
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listCompilations(
    ruleId: string,
  ): Promise<Envelope<WorkflowRuleCompilation[]> | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRuleCompilation[] }>(
        `/v1/workflow-rules/${ruleId}/compilations`,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async getCompilingState(
    workflowId: string,
  ): Promise<{ ruleIds: string[] } | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: { ruleIds: string[] } }>(
        `/v1/workflows/${workflowId}/workflow-rules/compiling-state`,
      );
      return response.data.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async listRunResults(
    runId: string,
  ): Promise<Envelope<WorkflowRuleResult[]> | ErrorFeeback> {
    try {
      const response = await this.httpClient.get<{ data: WorkflowRuleResult[] }>(
        `/v1/workflow-analysis-runs/${runId}/workflow-rule-results`,
      );
      return ok(response.data.data);
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
