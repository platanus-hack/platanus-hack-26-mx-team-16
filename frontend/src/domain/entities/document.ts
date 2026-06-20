import { DocumentType } from "./doctype";

export enum DocumentStatus {
  FOR_REVIEW = "for_review",
  CONFIRMED = "confirmed",
  ARCHIVED = "archived",
  REJECTED = "rejected",
}

export interface ExtractedFieldValue {
  fieldUuid: string;
  fieldName: string;
  fieldType: string;
  value: string | string[] | boolean | number | null;
  confidence?: number;
  validated?: boolean;
  correctedValue?: string | string[] | boolean | number | null;
}

export interface ExtractedData {
  fields: ExtractedFieldValue[];
  extractedAt?: string;
  processingTime?: number;
  pdfUrl?: string;
}

export interface Document {
  uuid: string;
  name: string;
  identifier?: string;
  doctype?: DocumentType;
  status: DocumentStatus;
  uploadedAt: string;
  confirmedAt?: string;
  fileSize: number;
  mimeType: string;
  workflowUuid: string;
  tags?: string[];
  extractedData?: ExtractedData;
}
