import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  KnowledgeDocumentListResponse,
  KnowledgeDocumentResponse,
} from "@/src/domain/responses/knowledge-document";
import type TaskResultResponse from "@/src/domain/responses/task-result";

export interface KnowledgeDocumentRepository {
  getAll(): Promise<KnowledgeDocumentListResponse | ErrorFeeback>;
  upload(file: File): Promise<KnowledgeDocumentResponse | ErrorFeeback>;
  delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback>;
}
