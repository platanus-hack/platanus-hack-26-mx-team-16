"use client";

import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  FileText,
  Loader2,
  X,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { memo, useEffect, useState } from "react";

import type {
  DocumentView,
  SetView,
} from "src/application/hooks/use-processing-job-events";
import { cn } from "src/application/lib/utils";
import { formatDuration } from "src/application/lib/format-duration";
import { DocumentStatus } from "src/domain/events/processing-job-event";
import {
  WorkflowProcessingJobStatus,
  type JobStep,
} from "src/domain/events/processing-job-event";
import { DateTimeLabel } from "src/presentation/components/common/date-time-label";
import { InlineMeta } from "src/presentation/components/common/inline-meta";
import { ShortId } from "src/presentation/components/common/short-id";
import { StatusRing } from "src/presentation/components/common/status-ring";
import {
  DOCUMENT_ROW_GRID,
  DocumentCard,
} from "src/presentation/workflows/cases/cards/document";

interface WorkflowProcessingJobRowProps {
  set: SetView;
  documents: DocumentView[];
  defaultExpanded?: boolean;
}

const STEP_LABELS: Record<JobStep, string> = {
  extract_text: "Leyendo texto",
  classify_pages: "Clasificando páginas",
  persist_documents: "Indexando documentos",
  extract_fields: "Extrayendo campos",
  validate_extraction: "Validando",
};

const STEP_ORDER: readonly JobStep[] = [
  "extract_text",
  "classify_pages",
  "persist_documents",
  "extract_fields",
  "validate_extraction",
] as const;

const STATUS_LABELS: Record<WorkflowProcessingJobStatus, string> = {
  PENDING: "En cola",
  RUNNING: "Ejecutando",
  PROCESSING: "Procesando",
  COMPLETED: "Listo",
  PARTIAL: "Parcial",
  FAILED: "FALLIDO",
};

const STATUS_RING_COLOR: Record<WorkflowProcessingJobStatus, string> = {
  PENDING: "text-muted-foreground",
  RUNNING: "text-violet-500",
  PROCESSING: "text-violet-500",
  COMPLETED: "text-emerald-600 dark:text-emerald-400",
  PARTIAL: "text-amber-600 dark:text-amber-400",
  FAILED: "text-red-600 dark:text-red-400",
};

// Background tonal aplicado al círculo en estados terminales — el icono
// queda recortado contra el color sin necesidad de un anillo decorativo.
const STATUS_RING_BG: Record<WorkflowProcessingJobStatus, string | undefined> = {
  PENDING: undefined,
  RUNNING: undefined,
  PROCESSING: undefined,
  COMPLETED: "bg-emerald-500/15",
  PARTIAL: "bg-amber-500/15",
  FAILED: "bg-red-500/15",
};

// Glifos sin círculo intrínseco para no chocar con el bg circular.
const STATUS_ICON: Record<WorkflowProcessingJobStatus, LucideIcon> = {
  PENDING: CircleDashed,
  RUNNING: Loader2,
  PROCESSING: Loader2,
  COMPLETED: Check,
  PARTIAL: AlertTriangle,
  FAILED: X,
};

const STATUS_TONE: Record<
  WorkflowProcessingJobStatus,
  { label: string; pill: string; dot: string }
> = {
  PENDING: {
    label: "en cola",
    pill: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground/40",
  },
  RUNNING: {
    label: "ejecutando",
    pill: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
    dot: "bg-violet-500 animate-pulse",
  },
  PROCESSING: {
    label: "procesando",
    pill: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
    dot: "bg-violet-500 animate-pulse",
  },
  COMPLETED: {
    label: "listo",
    pill: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  PARTIAL: {
    label: "parcial",
    pill: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  FAILED: {
    label: "falló",
    pill: "bg-red-500/10 text-red-700 dark:text-red-300",
    dot: "bg-red-500",
  },
};

function WorkflowProcessingJobRowImpl({
  set,
  documents,
  defaultExpanded = false,
}: WorkflowProcessingJobRowProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const isLive =
    set.status === WorkflowProcessingJobStatus.PROCESSING ||
    set.status === WorkflowProcessingJobStatus.RUNNING ||
    set.status === WorkflowProcessingJobStatus.PENDING;
  const stepLabel = set.currentStep ? STEP_LABELS[set.currentStep] : null;
  const stepOrdinal = set.currentStep
    ? STEP_ORDER.indexOf(set.currentStep) + 1
    : null;

  const sortedDocs = documents
    .slice()
    .sort((a, b) => (a.documentIndex ?? 0) - (b.documentIndex ?? 0));
  const docCount = sortedDocs.length;
  const docPassed = sortedDocs.filter(
    (d) => d.status === DocumentStatus.Completed
  ).length;
  const docFailed = sortedDocs.filter(
    (d) => d.status === DocumentStatus.Failed
  ).length;
  const docInflight = docCount - docPassed - docFailed;

  const displayId = set.temporalWorkflowId ?? set.setId;
  const elapsed = useProcessingDuration(set.startedAt, set.durationMs, isLive);
  const fallbackLabel = isLive
    ? (stepLabel ?? STATUS_LABELS[set.status])
    : STATUS_LABELS[set.status];
  const titleLine = set.fileName ?? fallbackLabel;

  const canExpand = docCount > 0;
  const isExpanded = canExpand && expanded;

  return (
    <li className="border-b border-border/40 last:border-b-0">
      <button
        type="button"
        onClick={() => {
          if (!canExpand) return;
          setExpanded((v) => !v);
        }}
        disabled={!canExpand}
        aria-expanded={canExpand ? isExpanded : undefined}
        className={cn(
          "group flex w-full items-center gap-4 px-4 py-3 text-left",
          "transition-colors",
          canExpand ? "cursor-pointer hover:bg-muted/50" : "cursor-default"
        )}
      >
        <StatusRing
          tone={STATUS_RING_COLOR[set.status]}
          bg={STATUS_RING_BG[set.status]}
          isLive={isLive}
          pct={set.progressPct}
          icon={STATUS_ICON[set.status]}
          spinIcon={false}
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <ShortId value={displayId} />
            <span className="truncate text-sm font-medium tracking-tight text-foreground">
              {titleLine}
            </span>
            {isLive && stepOrdinal ? (
              <span className="shrink-0 rounded bg-violet-500/15 px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-300">
                paso {stepOrdinal}/{STEP_ORDER.length}
              </span>
            ) : null}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <FileText
              className="size-3.5 shrink-0 text-muted-foreground"
              aria-hidden
            />
            <DateTimeLabel value={set.createdAt} />
            <InlineMeta>{elapsed}</InlineMeta>
            {isLive && stepLabel && set.fileName ? (
              <InlineMeta>{stepLabel}</InlineMeta>
            ) : null}
            <InlineMeta variant="error">{set.error?.message}</InlineMeta>
          </div>
        </div>

        <WorkflowProcessingJobOutcome
          isLive={isLive}
          docCount={docCount}
          passed={docPassed}
          failed={docFailed}
          inflight={docInflight}
        />

        <SetStatusBadge status={set.status} />

        {canExpand ? (
          <ChevronRight
            aria-hidden
            className={cn(
              "size-4 shrink-0 text-muted-foreground/60 transition-transform",
              isExpanded && "rotate-90"
            )}
          />
        ) : (
          <span aria-hidden className="size-4 shrink-0" />
        )}
      </button>

      {isExpanded ? (
        <ExpandedDocumentList documents={sortedDocs} isLive={isLive} />
      ) : null}
    </li>
  );
}

interface ExpandedDocumentListProps {
  documents: DocumentView[];
  isLive: boolean;
}

function ExpandedDocumentList({
  documents,
  isLive,
}: ExpandedDocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="px-4 pb-4 pt-1">
        <p className="px-1 text-xs italic text-muted-foreground">
          {isLive
            ? "Detectando documentos…"
            : "Este set no produjo documentos."}
        </p>
      </div>
    );
  }

  return (
    <div className="px-4 pb-4 pt-1">
      <div className="overflow-hidden rounded-md border border-border/40 bg-background/30">
        <DocumentTableHeader />
        <ul role="rowgroup" className="divide-y divide-border/30">
          {documents.map((doc) => (
            <li key={doc.documentId}>
              <DocumentCard document={doc} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function DocumentTableHeader() {
  return (
    <div
      role="row"
      className={cn(
        DOCUMENT_ROW_GRID,
        "px-3 py-1.5 border-b border-border/40 bg-muted/20",
        "font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground/60"
      )}
    >
      <span aria-hidden />
      <span>id</span>
      <span>tipo</span>
      <span>pág.</span>
      <span className="justify-self-end">extracción</span>
      <span className="justify-self-end">estado</span>
    </div>
  );
}

function SetStatusBadge({ status }: { status: WorkflowProcessingJobStatus }) {
  const tone = STATUS_TONE[status];
  return (
    <span
      className={`
        inline-flex shrink-0 items-center gap-1.5 self-center rounded-full
        border border-current/10 px-2 py-0.5
        font-mono text-[10px] uppercase tracking-[0.18em]
        ${tone.pill}
      `}
      title={`Estado: ${tone.label}`}
    >
      <span
        aria-hidden
        className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${tone.dot}`}
      />
      {tone.label}
    </span>
  );
}

interface DocumentOutcomeProps {
  isLive: boolean;
  docCount: number;
  passed: number;
  failed: number;
  inflight: number;
}

function WorkflowProcessingJobOutcome({
  isLive,
  docCount,
  passed,
  failed,
  inflight,
}: DocumentOutcomeProps) {
  if (isLive) {
    return (
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <span className="font-mono text-sm font-medium tabular-nums text-foreground/85">
          {passed + failed}
          <span className="text-muted-foreground/50">/{docCount || "?"}</span>
        </span>
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground/60">
          {docCount === 1 ? "doc" : "docs"}
        </span>
      </div>
    );
  }

  if (docCount === 0) return null;

  const safeTotal = passed + failed + inflight || 1;

  return (
    <div className="flex shrink-0 flex-col items-end gap-1.5">
      <div className="flex items-center gap-2.5 font-mono text-[11px] font-medium tabular-nums">
        <DocumentCountChip
          icon={CheckCircle2}
          count={passed}
          tone="text-emerald-700 dark:text-emerald-400"
          label={passed === 1 ? "documento listo" : "documentos listos"}
        />
        <DocumentCountChip
          icon={XCircle}
          count={failed}
          tone="text-red-700 dark:text-red-400"
          label={failed === 1 ? "documento falló" : "documentos fallaron"}
        />
        <DocumentCountChip
          icon={CircleDashed}
          count={inflight}
          tone="text-amber-700 dark:text-amber-400"
          label={inflight === 1 ? "documento en curso" : "documentos en curso"}
        />
      </div>
      <div
        className="flex h-1 w-24 overflow-hidden rounded-full bg-muted/40"
        aria-label="Distribución de documentos"
      >
        {passed > 0 ? (
          <span
            className="bg-emerald-500"
            style={{ width: `${(passed / safeTotal) * 100}%` }}
          />
        ) : null}
        {failed > 0 ? (
          <span
            className="bg-red-500"
            style={{ width: `${(failed / safeTotal) * 100}%` }}
          />
        ) : null}
        {inflight > 0 ? (
          <span
            className="bg-amber-500"
            style={{ width: `${(inflight / safeTotal) * 100}%` }}
          />
        ) : null}
      </div>
    </div>
  );
}

function DocumentCountChip({
  icon: Icon,
  count,
  tone,
  label,
}: {
  icon: LucideIcon;
  count: number;
  tone: string;
  label: string;
}) {
  if (count === 0) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 ${tone}`}
      title={`${count} ${label}`}
    >
      <Icon className="size-3" aria-hidden />
      {count}
    </span>
  );
}

/**
 * Wall-clock processing duration of the underlying Temporal run.
 *
 * Terminal: render the backend-precomputed `durationMs` (matches the
 * `finished_at - started_at` window stored on the row, identical to how
 * AnalysisRun exposes it). While live: tick once a second from
 * `startedAt` so the row counts up in real time.
 */
function useProcessingDuration(
  startedAt: string | null,
  durationMs: number | null,
  isLive: boolean
): string | null {
  const [tick, setTick] = useState(0);
  const ticking = isLive && durationMs == null;
  useEffect(() => {
    if (!ticking) return;
    const id = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [ticking]);

  if (durationMs != null) return formatDuration(durationMs);
  if (!startedAt) return null;
  const start = new Date(startedAt).getTime();
  if (Number.isNaN(start)) return null;
  void tick;
  return formatDuration(Date.now() - start);
}

export const WorkflowProcessingJobRow = memo(WorkflowProcessingJobRowImpl);
