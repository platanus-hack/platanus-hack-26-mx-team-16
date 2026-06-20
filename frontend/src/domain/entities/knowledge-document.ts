export type KnowledgeDocumentStatus = "vectorizing" | "ready" | "failed";

export type KnowledgeDocument = {
  uuid: string;
  fileName: string;
  mime: string;
  fileId: string | null;
  charCount: number;
  chunkCount: number;
  preview: string | null;
  status: KnowledgeDocumentStatus;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};
