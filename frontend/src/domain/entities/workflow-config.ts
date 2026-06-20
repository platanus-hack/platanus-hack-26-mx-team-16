import type { DocumentType } from "./doctype";

export enum WorkflowConfigStepType {
  EMAIL_UPLOAD = "email_upload",
  WHATSAPP_UPLOAD = "whatsapp_upload",
  INTEGRATIONS = "integrations",
  PRE_PROCESSING = "pre_processing",
  SPLITTING = "splitting",
  CLASSIFICATION = "classification",
  EXTRACTION = "extraction",
  VALIDATION = "validation",
  ANALYSIS = "analysis",
  DATA_EXPORT = "data_export",
}

export enum WorkflowConfigStepStatus {
  NOT_CONFIGURED = "not_configured",
  CONFIGURED = "configured",
  DISABLED = "disabled",
}

export interface WorkflowConfigExtractionDocumentType {
  doctype: DocumentType;
  fieldsCount: number;
  checksCount: number;
}

export interface WorkflowConfigStep {
  uuid: string;
  type: WorkflowConfigStepType;
  title: string;
  description: string;
  status: WorkflowConfigStepStatus;
  order: number;
  // For extraction step
  extractionDoctypes?: WorkflowConfigExtractionDocumentType[];
}

export interface WorkflowConfig {
  uuid: string;
  workflowUuid: string;
  steps: WorkflowConfigStep[];
  createdAt: string;
  updatedAt: string;
}
