import type { DocumentType } from "@/src/domain/entities/doctype";

export interface DocumentTypeResponse {
  data: DocumentType;
  datetime: string;
}

export interface DocumentTypeListResponse {
  data: DocumentType[];
  datetime: string;
}
