export enum WorkflowDocumentStatus {
  EMPTY = "EMPTY",
  UPLOADED = "UPLOADED",
  PROCESSING = "PROCESSING",
  EXTRACTED = "EXTRACTED",
  ERROR = "ERROR",
}

export interface StatDelta {
  value: number;
  deltaPct: number | null;
}

export interface QueueDelta {
  value: number;
  deltaSinceLastHour: number | null;
}

export interface OverviewSummary {
  totalDocuments: StatDelta;
  documentsProcessed: StatDelta;
  activeWorkflows: StatDelta;
  processingQueue: QueueDelta;
}

export interface ThroughputBucket {
  label: string;
  year: number;
  month: number;
  total: number;
}

export interface RecentDocument {
  uuid: string;
  name: string;
  workflowSlug: string;
  workflowName: string;
  status: WorkflowDocumentStatus | string;
  pageCount: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface OverviewData {
  summary: OverviewSummary;
  throughput: ThroughputBucket[];
  recentDocuments: RecentDocument[];
}
