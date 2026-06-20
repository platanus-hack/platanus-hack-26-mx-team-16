import type {
  KnowledgeListResponse,
  KnowledgeResponse,
} from "@/src/domain/responses/knowledge";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";

export interface KnowledgeRepository {
  getAll(): Promise<KnowledgeListResponse | ErrorFeeback>;
  getById(uuid: string): Promise<KnowledgeResponse | ErrorFeeback>;
  create(
    name: string,
    description: string
  ): Promise<KnowledgeResponse | ErrorFeeback>;
  update(
    uuid: string,
    name: string,
    description: string
  ): Promise<KnowledgeResponse | ErrorFeeback>;
  delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback>;
  duplicate(uuid: string): Promise<KnowledgeResponse | ErrorFeeback>;
}
