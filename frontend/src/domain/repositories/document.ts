import type { ErrorFeeback } from "../errors/error-feeback";
import type {
  DocumentResponse,
  DocumentListResponse,
} from "../responses/document";
import type TaskResultResponse from "../responses/task-result";

export interface DocumentRepository {
  getAll(workflowUuid: string): Promise<DocumentListResponse | ErrorFeeback>;
  getById(uuid: string): Promise<DocumentResponse | ErrorFeeback>;
  delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback>;
}
