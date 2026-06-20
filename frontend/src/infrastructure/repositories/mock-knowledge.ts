import type { KnowledgeRepository } from "@/src/domain/repositories/knowledge";
import type {
  KnowledgeListResponse,
  KnowledgeResponse,
} from "@/src/domain/responses/knowledge";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type TaskResultResponse from "@/src/domain/responses/task-result";
import { successTask } from "@/src/domain/responses/task-result";
import type { Knowledge } from "@/src/domain/entities/knowledge";

export class MockKnowledgeRepository implements KnowledgeRepository {
  private knowledge: Knowledge[] = [
    {
      uuid: "kb-1",
      name: "_tripto-ws-prod-tripto-ws-api-1_logs (2).txt",
      description:
        "useful for when you want to answer queries about the _tripto-ws-prod-tripto-ws-api-1_logs (2).txt",
      docCount: 1,
      totalDocs: 1,
      status: ["PROCESSING", "PROD"],
      updatedAt: new Date(Date.now() - 10000).toISOString(),
      owner: {
        name: "Victor Aguilar C.",
      },
    },
    {
      uuid: "kb-2",
      name: "aaa",
      description: "",
      docCount: 0,
      totalDocs: 1,
      status: ["PROD"],
      updatedAt: new Date(Date.now() - 2592000000).toISOString(),
      owner: {
        name: "Victor Aguilar C.",
      },
    },
  ];

  async getAll(): Promise<KnowledgeListResponse | ErrorFeeback> {
    return {
      data: this.knowledge,
      datetime: new Date().toISOString(),
    };
  }

  async getById(uuid: string): Promise<KnowledgeResponse | ErrorFeeback> {
    const item = this.knowledge.find((k) => k.uuid === uuid);
    if (!item) {
      return {
        errors: [{ message: "Knowledge not found", code: "NOT_FOUND" }],
        validation: null,
      };
    }
    return {
      data: item,
      datetime: new Date().toISOString(),
    };
  }

  async create(
    name: string,
    description: string
  ): Promise<KnowledgeResponse | ErrorFeeback> {
    const newKnowledge: Knowledge = {
      uuid: `kb-${Date.now()}`,
      name,
      description,
      docCount: 0,
      totalDocs: 0,
      status: [],
      updatedAt: new Date().toISOString(),
      owner: {
        name: "Victor Aguilar C.",
      },
    };

    this.knowledge.push(newKnowledge);

    return {
      data: newKnowledge,
      datetime: new Date().toISOString(),
    };
  }

  async update(
    uuid: string,
    name: string,
    description: string
  ): Promise<KnowledgeResponse | ErrorFeeback> {
    const index = this.knowledge.findIndex((k) => k.uuid === uuid);
    if (index === -1) {
      return {
        errors: [{ message: "Knowledge not found", code: "NOT_FOUND" }],
        validation: null,
      };
    }

    this.knowledge[index] = {
      ...this.knowledge[index],
      name,
      description,
      updatedAt: new Date().toISOString(),
    };

    return {
      data: this.knowledge[index],
      datetime: new Date().toISOString(),
    };
  }

  async delete(uuid: string): Promise<TaskResultResponse | ErrorFeeback> {
    const index = this.knowledge.findIndex((k) => k.uuid === uuid);
    if (index === -1) {
      return {
        errors: [{ message: "Knowledge not found", code: "NOT_FOUND" }],
        validation: null,
      };
    }

    this.knowledge.splice(index, 1);

    return successTask;
  }

  async duplicate(uuid: string): Promise<KnowledgeResponse | ErrorFeeback> {
    const original = this.knowledge.find((k) => k.uuid === uuid);
    if (!original) {
      return {
        errors: [{ message: "Knowledge not found", code: "NOT_FOUND" }],
        validation: null,
      };
    }

    const duplicated: Knowledge = {
      ...original,
      uuid: `kb-${Date.now()}`,
      name: `${original.name} (Copy)`,
      updatedAt: new Date().toISOString(),
    };

    this.knowledge.push(duplicated);

    return {
      data: duplicated,
      datetime: new Date().toISOString(),
    };
  }
}
