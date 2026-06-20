/**
 * AWS Textract Response Types
 *
 * Types for AWS Textract Expense Analysis API responses
 */

export interface BoundingBox {
  Width: number;
  Height: number;
  Left: number;
  Top: number;
}

export interface Point {
  X: number;
  Y: number;
}

export interface Geometry {
  BoundingBox: BoundingBox;
  Polygon: Point[];
}

export interface TypeField {
  Text: string;
  Confidence: number;
}

export interface Detection {
  Text: string;
  Geometry: Geometry;
  Confidence: number;
}

export interface GroupProperty {
  Types: string[];
  Id: string;
}

export interface SummaryField {
  Type: TypeField;
  LabelDetection?: Detection;
  ValueDetection?: Detection;
  PageNumber: number;
  GroupProperties?: GroupProperty[];
}

export interface LineItem {
  LineItemExpenseFields: {
    Type: TypeField;
    LabelDetection?: Detection;
    ValueDetection?: Detection;
    PageNumber: number;
    GroupProperties?: GroupProperty[];
  }[];
}

export interface ExpenseDocument {
  ExpenseIndex: number;
  SummaryFields: SummaryField[];
  LineItemGroups?: {
    LineItemGroupIndex: number;
    LineItems: LineItem[];
  }[];
}

export interface DocumentMetadata {
  Pages: number;
}

export interface AnalyzeExpenseResponse {
  DocumentMetadata: DocumentMetadata;
  JobStatus: string;
  ExpenseDocuments: ExpenseDocument[];
}

/**
 * AWS Textract AnalyzeDocument Response Types
 */
export interface TextractBlock {
  BlockType: string;
  Confidence?: number;
  Text?: string;
  Geometry: Geometry;
  Id: string;
  Relationships?: {
    Type: string;
    Ids: string[];
  }[];
  Page?: number;
  EntityTypes?: string[];
}

export interface AnalyzeDocumentResponse {
  AnalyzeDocumentModelVersion?: string;
  Blocks: TextractBlock[];
  Bucket?: string;
  DocumentMetadata: DocumentMetadata;
  JobStatus: string;
  UploadedFileName?: string;
}

/**
 * Helper types for rendering coordinates
 */
export interface CoordinateBox {
  id: string;
  text: string;
  type: string;
  boundingBox: BoundingBox;
  confidence: number;
  color?: string;
  groupId?: string;
  /** 1-based page index from Textract; defaults to 1 when missing. */
  page?: number;
}
