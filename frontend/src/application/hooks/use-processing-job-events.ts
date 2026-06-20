"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  useTransition,
} from "react";
import {
  type ProcessingJobEventEnvelope,
  ProcessingJobEventType,
  DocumentStatus,
  WorkflowProcessingJobStatus,
  type JobStep,
} from "@/src/domain/events/processing-job-event";
import {
  type ConnectionState,
  subscribeSSE,
} from "@/src/infrastructure/http/sse";

/**
 * Live view of a single processing_job as it moves through the Temporal
 * workflow. The reducer aggregates dispatched, step_started,
 * step_completed, completed, and failed events into a single object
 * the UI can render directly.
 */
export interface SetView {
  setId: string;
  temporalWorkflowId: string | null;
  workflowCaseId: string | null;
  fileId: string | null;
  fileName: string | null;
  status: WorkflowProcessingJobStatus;
  currentStep: JobStep | null;
  /** 0-100; advances as each pipeline step completes. */
  progressPct: number;
  error: { code: string; message: string; sourceStep: string } | null;
  lastSeq: number;
  createdAt: string | null;
  /** Wall-clock window of the underlying Temporal run. */
  startedAt: string | null;
  finishedAt: string | null;
  /** Backend-precomputed duration; null while the set is in flight. */
  durationMs: number | null;
  resultSummary: Record<string, unknown> | null;
}

/**
 * Live view of a document persisted by the workflow's `persist_documents`
 * step. Only `processing_job.document_persisted` events feed this map; we
 * don't currently track per-document extracting/validating state because
 * the unified event stream emits step transitions at the *set* level.
 */
export interface DocumentView {
  documentId: string;
  processingJobId: string;
  documentTypeId: string | null;
  documentTypeName: string | null;
  documentIndex: number | null;
  pageRange: { from: number; to: number } | null;
  status: DocumentStatus;
  fieldCount: number | null;
  validationPassCount: number | null;
  validationFailCount: number | null;
}

export interface ProcessingJobEventsState {
  sets: Record<string, SetView>;
  documents: Record<string, DocumentView>;
  /** Per-set monotonic seq for de-dupe — see comment in reducer. */
  lastSeqBySet: Record<string, number>;
  /** Max seq across all sets — passed as `?since_seq=` on (re)connect. */
  lastSeq: number;
  isHydrated: boolean;
}

export type ProcessingJobEventsAction =
  | { type: "hydrate"; lastSeq: number }
  | { type: "event"; event: ProcessingJobEventEnvelope };

/**
 * The backend SSE wire format uses snake_case (processing_job_id, workflow_id,
 * workflow_case_id, document_id); accept either casing and project to the
 * camelCase envelope the reducer reads.
 */
function normalizeEnvelope(raw: unknown): ProcessingJobEventEnvelope {
  const r = raw as Record<string, unknown>;
  return {
    seq: r.seq as number,
    ts: r.ts as string,
    type: r.type as ProcessingJobEventEnvelope["type"],
    workflowId: (r.workflowId ?? r.workflow_id) as string,
    processingJobId: (r.processingJobId ?? r.processing_job_id) as string,
    workflowCaseId: (r.workflowCaseId ?? r.workflow_case_id) as
      | string
      | null
      | undefined,
    documentId: (r.documentId ?? r.document_id) as string | null | undefined,
    payload: (r.payload ?? {}) as Record<string, unknown>,
  };
}

export const INITIAL_STATE: ProcessingJobEventsState = {
  sets: {},
  documents: {},
  lastSeqBySet: {},
  lastSeq: 0,
  isHydrated: false,
};

// Step ordinals used to compute `progressPct` from `step_completed`
// events. Must match `JobStep` order.
const STEP_ORDER: readonly JobStep[] = [
  "extract_text",
  "classify_pages",
  "persist_documents",
  "extract_fields",
  "validate_extraction",
] as const;

function progressFromStep(step: JobStep | null | undefined): number {
  if (!step) return 0;
  const idx = STEP_ORDER.indexOf(step);
  if (idx < 0) return 0;
  return Math.round(((idx + 1) / STEP_ORDER.length) * 100);
}

function computeDurationMs(
  payload: Record<string, unknown>,
  startedAt: string | null | undefined,
  finishedAt: string | null | undefined
): number | null {
  const fromPayload =
    (payload.durationMs as number | null | undefined) ??
    (payload.duration_ms as number | null | undefined);
  if (fromPayload != null) return fromPayload;
  if (!startedAt || !finishedAt) return null;
  const start = new Date(startedAt).getTime();
  const end = new Date(finishedAt).getTime();
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return end - start;
}

function ensureSet(
  state: ProcessingJobEventsState,
  setId: string,
  ev: ProcessingJobEventEnvelope
): SetView {
  return (
    state.sets[setId] ?? {
      setId,
      temporalWorkflowId: null,
      workflowCaseId: ev.workflowCaseId ?? null,
      fileId: null,
      fileName: null,
      status: WorkflowProcessingJobStatus.PENDING,
      currentStep: null,
      progressPct: 0,
      error: null,
      lastSeq: 0,
      createdAt: ev.ts,
      startedAt: null,
      finishedAt: null,
      durationMs: null,
      resultSummary: null,
    }
  );
}

export function reducer(
  state: ProcessingJobEventsState,
  action: ProcessingJobEventsAction
): ProcessingJobEventsState {
  if (action.type === "hydrate") {
    return { ...state, lastSeq: action.lastSeq, isHydrated: true };
  }

  const ev = action.event;
  // Per-set seq de-dupe. Each set has its own monotonic counter so a
  // fresh dispatch's events shouldn't be dropped just because an older
  // set in the same workflow already advanced lastSeq.
  const lastSeqForSet = state.lastSeqBySet[ev.processingJobId] ?? 0;
  if (ev.seq <= lastSeqForSet) return state;

  const next = applyEvent(state, ev);
  return {
    ...next,
    lastSeq: Math.max(state.lastSeq, ev.seq),
    lastSeqBySet: { ...state.lastSeqBySet, [ev.processingJobId]: ev.seq },
  };
}

function applyEvent(
  state: ProcessingJobEventsState,
  ev: ProcessingJobEventEnvelope
): ProcessingJobEventsState {
  switch (ev.type) {
    case ProcessingJobEventType.Dispatched: {
      const p = ev.payload as Record<string, unknown>;
      const fileId =
        (p.fileId as string | null | undefined) ??
        (p.file_id as string | null | undefined) ??
        null;
      const fileName =
        (p.fileName as string | null | undefined) ??
        (p.file_name as string | null | undefined) ??
        null;
      const temporalWorkflowId =
        (p.temporalWorkflowId as string | null | undefined) ??
        (p.processing_job_id as string | null | undefined) ??
        (p.temporalJobId as string | null | undefined) ??
        (p.temporal_job_id as string | null | undefined) ??
        null;
      const startedAt =
        (p.startedAt as string | null | undefined) ??
        (p.started_at as string | null | undefined) ??
        ev.ts ??
        null;
      const existing = ensureSet(state, ev.processingJobId, ev);
      const nextSet: SetView = {
        ...existing,
        temporalWorkflowId: temporalWorkflowId ?? existing.temporalWorkflowId,
        fileId: fileId ?? existing.fileId,
        fileName: fileName ?? existing.fileName,
        workflowCaseId: ev.workflowCaseId ?? existing.workflowCaseId,
        startedAt: existing.startedAt ?? startedAt,
        status: WorkflowProcessingJobStatus.PROCESSING,
        lastSeq: ev.seq,
      };
      return {
        ...state,
        sets: { ...state.sets, [ev.processingJobId]: nextSet },
      };
    }
    case ProcessingJobEventType.StepStarted: {
      const step = ev.payload.step as JobStep | undefined;
      const existing = ensureSet(state, ev.processingJobId, ev);
      return {
        ...state,
        sets: {
          ...state.sets,
          [ev.processingJobId]: {
            ...existing,
            status: WorkflowProcessingJobStatus.PROCESSING,
            currentStep: step ?? existing.currentStep,
            lastSeq: ev.seq,
          },
        },
      };
    }
    case ProcessingJobEventType.StepCompleted: {
      const step = ev.payload.step as JobStep | undefined;
      const existing = ensureSet(state, ev.processingJobId, ev);
      return {
        ...state,
        sets: {
          ...state.sets,
          [ev.processingJobId]: {
            ...existing,
            currentStep: step ?? existing.currentStep,
            progressPct: Math.max(
              existing.progressPct,
              progressFromStep(step ?? existing.currentStep)
            ),
            lastSeq: ev.seq,
          },
        },
      };
    }
    case ProcessingJobEventType.DocumentPersisted: {
      // Backend emits payload in snake_case (workflow Pydantic + replay
      // endpoint) but the DTO is camelCase. Tolerate both shapes.
      const p = ev.payload as Record<string, unknown>;
      const documentId =
        (p.documentId as string | undefined) ??
        (p.document_id as string | undefined) ??
        ev.documentId ??
        null;
      const existing = ensureSet(state, ev.processingJobId, ev);
      if (!documentId) {
        return {
          ...state,
          sets: {
            ...state.sets,
            [ev.processingJobId]: { ...existing, lastSeq: ev.seq },
          },
        };
      }
      const documentTypeId =
        (p.documentTypeId as string | null | undefined) ??
        (p.document_type_id as string | null | undefined) ??
        null;
      const documentTypeName =
        (p.documentTypeName as string | null | undefined) ??
        (p.document_type_name as string | null | undefined) ??
        null;
      const documentIndex =
        (p.documentIndex as number | null | undefined) ??
        (p.document_index as number | null | undefined) ??
        null;
      const pageRange =
        (p.pageRange as { from: number; to: number } | null | undefined) ??
        (p.page_range as { from: number; to: number } | null | undefined) ??
        null;
      const processingStatus =
        (p.processingStatus as string | undefined) ??
        (p.processing_status as string | undefined);
      const status: DocumentStatus =
        processingStatus === "completed"
          ? DocumentStatus.Completed
          : processingStatus === "failed"
            ? DocumentStatus.Failed
            : (state.documents[documentId]?.status ?? DocumentStatus.Pending);
      const summary =
        (p.summary as Record<string, unknown> | undefined) ?? null;
      const previous = state.documents[documentId];
      const fieldCount =
        summary != null
          ? ((summary.extractedFieldCount as number | null | undefined) ??
            (summary.extracted_field_count as number | null | undefined) ??
            null)
          : (previous?.fieldCount ?? null);
      const validationPassCount =
        summary != null
          ? ((summary.validationPassCount as number | null | undefined) ??
            (summary.validation_pass_count as number | null | undefined) ??
            null)
          : (previous?.validationPassCount ?? null);
      const validationFailCount =
        summary != null
          ? ((summary.validationFailCount as number | null | undefined) ??
            (summary.validation_fail_count as number | null | undefined) ??
            null)
          : (previous?.validationFailCount ?? null);
      return {
        ...state,
        sets: {
          ...state.sets,
          [ev.processingJobId]: { ...existing, lastSeq: ev.seq },
        },
        documents: {
          ...state.documents,
          [documentId]: {
            documentId,
            processingJobId: ev.processingJobId,
            documentTypeId,
            documentTypeName,
            documentIndex,
            pageRange,
            status,
            fieldCount,
            validationPassCount,
            validationFailCount,
          },
        },
      };
    }
    case ProcessingJobEventType.Completed: {
      const existing = ensureSet(state, ev.processingJobId, ev);
      const p = ev.payload as Record<string, unknown>;
      const summary =
        (p.summary as Record<string, unknown> | undefined) ?? null;
      const status =
        (p.status as WorkflowProcessingJobStatus | undefined) ??
        WorkflowProcessingJobStatus.COMPLETED;
      const fileName =
        (p.fileName as string | null | undefined) ??
        (p.file_name as string | null | undefined) ??
        existing.fileName;
      const startedAt =
        (p.startedAt as string | null | undefined) ??
        (p.started_at as string | null | undefined) ??
        existing.startedAt;
      const finishedAt =
        (p.finishedAt as string | null | undefined) ??
        (p.finished_at as string | null | undefined) ??
        ev.ts ??
        null;
      const durationMs = computeDurationMs(p, startedAt, finishedAt);
      return {
        ...state,
        sets: {
          ...state.sets,
          [ev.processingJobId]: {
            ...existing,
            fileName,
            startedAt,
            finishedAt,
            durationMs,
            status,
            progressPct: 100,
            resultSummary: summary,
            lastSeq: ev.seq,
          },
        },
      };
    }
    case ProcessingJobEventType.Failed: {
      const existing = ensureSet(state, ev.processingJobId, ev);
      const p = ev.payload as Record<string, unknown>;
      const fileName =
        (p.fileName as string | null | undefined) ??
        (p.file_name as string | null | undefined) ??
        existing.fileName;
      const startedAt =
        (p.startedAt as string | null | undefined) ??
        (p.started_at as string | null | undefined) ??
        existing.startedAt;
      const finishedAt =
        (p.finishedAt as string | null | undefined) ??
        (p.finished_at as string | null | undefined) ??
        ev.ts ??
        null;
      const durationMs = computeDurationMs(p, startedAt, finishedAt);
      return {
        ...state,
        sets: {
          ...state.sets,
          [ev.processingJobId]: {
            ...existing,
            fileName,
            startedAt,
            finishedAt,
            durationMs,
            status: WorkflowProcessingJobStatus.FAILED,
            error: {
              code:
                (p.errorCode as string) ??
                (p.error_code as string) ??
                "extraction.error",
              message: (p.message as string) ?? "Extraction failed",
              sourceStep:
                (p.sourceStep as string) ?? (p.source_step as string) ?? "",
            },
            lastSeq: ev.seq,
          },
        },
      };
    }
    default:
      return state;
  }
}

export interface UseProcessingJobEventsOptions {
  workflowId: string;
  workflowCaseId?: string;
}

export interface UseProcessingJobEventsResult {
  sets: SetView[];
  documents: DocumentView[];
  connectionState: ConnectionState;
  isHydrated: boolean;
}

/**
 * Live SSE consumer for the unified processing_job event stream. Replaces
 * the legacy `useCaseEvents` hook one-to-one — STANDARD workflows omit
 * `workflowCaseId`, ANALYSIS workflows pass it.
 *
 * Pattern (per spec §7.1, post-unification):
 * 1. Open EventSource at /events?since_seq=0&workflowCaseId=…; the
 *    backend replays missed events from PG before forwarding the live
 *    Redis stream.
 * 2. Reducer aggregates events into a Map<setId, SetView> +
 *    Map<documentId, DocumentView>.
 * 3. Reconnect with the latest seq on transport drops.
 */
export function useProcessingJobEvents({
  workflowId,
  workflowCaseId,
}: UseProcessingJobEventsOptions): UseProcessingJobEventsResult {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("idle");
  const [, startEventTransition] = useTransition();
  const lastSeqRef = useRef(0);
  const closeRef = useRef<(() => void) | null>(null);

  // Keep lastSeqRef in sync with state for reconnects.
  lastSeqRef.current = state.lastSeq;

  const markHydrated = useCallback(() => {
    dispatch({ type: "hydrate", lastSeq: lastSeqRef.current });
  }, []);

  useEffect(() => {
    const wasConnectedRef = { current: false };

    const buildUrl = () => {
      const params = new URLSearchParams();
      params.set("since_seq", String(lastSeqRef.current));
      if (workflowCaseId) params.set("workflowCaseId", workflowCaseId);
      return `/api/v1/workflows/${workflowId}/jobs/events?${params.toString()}`;
    };

    const close = subscribeSSE(buildUrl, {
      onOpen: () => {
        // First open marks the stream as hydrated so the UI can drop the
        // skeleton state. There's no separate /state snapshot for the
        // unified stream — the PG replay window seeds the reducer.
        if (!wasConnectedRef.current) {
          markHydrated();
        }
        wasConnectedRef.current = true;
      },
      onStateChange: setConnectionState,
      onEvent: (raw) => {
        if (raw.type === "ready" || raw.type === "heartbeat") return;
        if (!raw.data) return;
        let event: ProcessingJobEventEnvelope;
        try {
          event = normalizeEnvelope(JSON.parse(raw.data));
        } catch {
          return;
        }
        if (typeof event?.seq !== "number") return;
        if (typeof event.processingJobId !== "string") return;
        startEventTransition(() => {
          dispatch({ type: "event", event });
        });
      },
    });
    closeRef.current = close;

    return () => {
      closeRef.current?.();
      closeRef.current = null;
    };
  }, [workflowId, workflowCaseId, markHydrated]);

  // Sort sets newest first (createdAt); documents by index ascending.
  const sets = useMemo(
    () =>
      Object.values(state.sets).sort((a, b) => {
        if (a.createdAt && b.createdAt)
          return b.createdAt.localeCompare(a.createdAt);
        return 0;
      }),
    [state.sets]
  );
  const documents = useMemo(
    () =>
      Object.values(state.documents).sort(
        (a, b) => (a.documentIndex ?? 0) - (b.documentIndex ?? 0)
      ),
    [state.documents]
  );

  return {
    sets,
    documents,
    connectionState,
    isHydrated: state.isHydrated,
  };
}
