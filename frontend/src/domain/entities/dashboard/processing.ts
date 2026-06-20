export enum PipelineStageKey {
  UPLOAD = "UPLOAD",
  OCR = "OCR",
  EXTRACTION = "EXTRACTION",
  VALIDATION = "VALIDATION",
  PROCESSING = "PROCESSING",
  COMPLETE = "COMPLETE",
}

export interface ProcessingSummary {
  inQueue: number;
  processing: number;
  completedToday: number;
  failed: number;
  /**
   * Null when no documents completed today — the SQL `AVG` over an empty
   * set returns NULL and is forwarded straight through to the frontend.
   * UI renders "—" in this case.
   */
  avgProcessingSeconds: number | null;
}

export interface PipelineStage {
  stage: PipelineStageKey | string;
  label: string;
  count: number;
}

export interface LiveProcessingDocument {
  uuid: string;
  name: string;
  stage: PipelineStageKey | string;
  progressPct: number;
  /**
   * Null when the document has already exceeded the global average
   * processing time, or when the average itself is unknown. UI renders "—".
   */
  etaSeconds: number | null;
  startedAt: string;
}

export interface ProcessingData {
  summary: ProcessingSummary;
  stages: PipelineStage[];
  liveProcessing: LiveProcessingDocument[];
}
