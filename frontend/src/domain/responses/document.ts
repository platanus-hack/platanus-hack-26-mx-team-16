import type { Document } from "../entities/document";

export interface DocumentResponse {
  data: Document;
  datetime: string;
}

export interface DocumentListResponse {
  data: Document[];
  datetime: string;
}
