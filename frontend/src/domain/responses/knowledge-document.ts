import type { KnowledgeDocument } from "@/src/domain/entities/knowledge-document";

export type KnowledgeDocumentResponse = {
  data: KnowledgeDocument;
  datetime: string;
};

export type KnowledgeDocumentListResponse = {
  data: KnowledgeDocument[];
  datetime: string;
};
