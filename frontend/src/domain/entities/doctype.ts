export enum FieldType {
  TEXT = "text",
  EMAIL = "email",
  PHONE = "phone",
  LOCATION = "location",
  DATE = "date",
  NUMBER = "number",
  TEXTAREA = "textarea",
  SELECT = "select",
  MULTISELECT = "multiselect",
  CHECKBOX = "checkbox",
  FILE = "file",
  OBJECT = "object",
  ARRAY = "array",
}

export interface DocumentTypeField {
  uuid: string;
  name: string;
  type: FieldType;
  icon?: string;
  required: boolean;
  enabled: boolean;
  order: number;
  description?: string;
  aiPrompt?: string;
  allowMultipleValues?: boolean;
  noRectangle?: boolean;
  manualEntryOnly?: boolean;
  slug?: string;
  alternatives?: string;
  locationHint?: string;
  examples?: string[];
  keywords?: string[];
  children?: DocumentTypeField[];
}

export interface ValidationRule {
  uuid: string;
  name: string;
  enabled: boolean;
  description?: string;
  type: "document" | "field";
  prompt?: string;
  missingDataHandling?: "skip" | "fail" | "pass" | "ignore";
  code?: string;
}

export interface DocumentType {
  uuid: string;
  workflowId?: string;
  name: string;
  slug?: string;
  description: string;
  workflowCount?: number;
  fieldsCount?: number;
  checksCount?: number;
  sampleDocument?: string;
  referenceDocumentUrl?: string;
  textractCoordinatesUrl?: string;
  sampleFileId?: string;
  sampleFileText?: boolean;
  validationRules?: ValidationRule[];
  fields?: Record<string, unknown>;
  keywords?: string[];
  examples?: string[];
}
