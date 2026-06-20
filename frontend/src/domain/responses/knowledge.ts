import type { Knowledge } from "@/src/domain/entities/knowledge";

export interface KnowledgeResponse {
  data: Knowledge;
  datetime: string;
}

export interface KnowledgeListResponse {
  data: Knowledge[];
  datetime: string;
}
