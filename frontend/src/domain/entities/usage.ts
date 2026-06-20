export interface ProcessRecord {
  uuid: string;
  tenantId: string;
  workflowId: string | null;
  workflowName: string | null;
  objectKeyDigest: string;
  pageCount: number;
  analysisRunId: string | null;
  processedAt: string;
  createdAt: string;
}

export interface UsageSummary {
  pagesUsed: number;
  monthlyQuota: number | null;
  usagePct: number | null;
  isAtLimit: boolean;
  isNearLimit: boolean;
  periodStart: string;
  periodEnd: string;
  daysRemaining: number;
}

export interface ProcessRecordPage {
  data: ProcessRecord[];
  pagination: { nextCursor: string | null; limit: number };
}
