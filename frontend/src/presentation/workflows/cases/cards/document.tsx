"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { memo } from "react";
import type { DocumentView } from "src/application/hooks/use-processing-job-events";
import { cn } from "src/application/lib/utils";
import { DocumentStatus } from "src/domain/events/processing-job-event";
import { ShortId } from "src/presentation/components/common/short-id";

interface DocumentCardProps {
  document: DocumentView;
}

// Single-color dots replace the previous ring + check/x glyph. Reason:
// the parent WorkflowProcessingJob row already paints a status ring with
// its own check icon — repeating checkmarks per document made the
// expanded view look like a forest of confirmations.
const STATUS_DOT: Record<DocumentStatus, string> = {
  pending: "bg-muted-foreground/40",
  extracting: "bg-blue-500 animate-pulse",
  validating: "bg-violet-500 animate-pulse",
  completed: "bg-emerald-500",
  failed: "bg-rose-500",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "queued",
  extracting: "extracting",
  validating: "validating",
  completed: "done",
  failed: "failed",
};

const STATUS_LABEL_TONE: Record<DocumentStatus, string> = {
  pending: "text-muted-foreground/70",
  extracting: "text-blue-700 dark:text-blue-300",
  validating: "text-violet-700 dark:text-violet-300",
  completed: "text-emerald-700 dark:text-emerald-400",
  failed: "text-rose-700 dark:text-rose-400",
};

export const DOCUMENT_ROW_GRID =
  "grid items-center gap-3 grid-cols-[10px_minmax(96px,auto)_minmax(0,1fr)_72px_minmax(108px,auto)_64px]";

function DocumentCardImpl({ document: doc }: DocumentCardProps) {
  const status = doc.status ?? DocumentStatus.Pending;
  const range = doc.pageRange;
  const rangeLabel = range
    ? range.from === range.to
      ? `p. ${range.from}`
      : `p. ${range.from}–${range.to}`
    : null;
  const passed = doc.validationPassCount;
  const failed = doc.validationFailCount;
  const hasValidations = passed != null || failed != null;
  const validationTotal = (passed ?? 0) + (failed ?? 0);

  const params = useParams<{ wfSlug?: string }>();
  const workflowSlug = params?.wfSlug;
  const detailHref = workflowSlug
    ? `/workflows/${workflowSlug}/documents/${doc.documentId}`
    : null;

  const className = cn(
    DOCUMENT_ROW_GRID,
    "px-3 py-2 text-sm",
    "transition-colors hover:bg-muted/40",
    "focus-visible:outline-none focus-visible:bg-muted/40",
    status === DocumentStatus.Failed && "bg-rose-500/[0.04]",
    detailHref && "cursor-pointer"
  );

  const content = (
    <>
      <span
        aria-hidden
        className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[status])}
        title={STATUS_LABEL[status]}
      />
      <ShortId value={doc.documentId} className="text-muted-foreground/70" />
      <span className="truncate font-medium text-foreground/90">
        {doc.documentTypeName ?? "—"}
      </span>
      <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider tabular-nums text-muted-foreground/80">
        {rangeLabel ?? "—"}
      </span>
      <div className="flex items-baseline justify-end gap-3 font-mono text-[11px] tabular-nums">
        <Metric
          value={doc.fieldCount}
          label="fields"
          tone="text-foreground/80"
        />
        {hasValidations ? (
          <Metric
            value={`${passed ?? 0}/${validationTotal}`}
            label="valid"
            tone={
              (failed ?? 0) > 0
                ? "text-rose-700 dark:text-rose-400"
                : "text-emerald-700 dark:text-emerald-400"
            }
            title={`${passed ?? 0} pasaron · ${failed ?? 0} fallaron`}
          />
        ) : (
          <Metric value={null} label="valid" tone="text-foreground/80" />
        )}
      </div>
      <span
        className={cn(
          "justify-self-end shrink-0 font-mono text-[10px] uppercase tracking-[0.16em]",
          STATUS_LABEL_TONE[status]
        )}
      >
        {STATUS_LABEL[status]}
      </span>
    </>
  );

  if (detailHref) {
    return (
      <Link
        href={detailHref}
        role="row"
        aria-label={`Abrir detalle de ${doc.documentTypeName ?? doc.documentId}`}
        className={className}
      >
        {content}
      </Link>
    );
  }

  return (
    <div role="row" className={className}>
      {content}
    </div>
  );
}

function Metric({
  value,
  label,
  tone,
  title,
}: {
  value: number | string | null;
  label: string;
  tone: string;
  title?: string;
}) {
  if (value == null) {
    return (
      <span className="text-muted-foreground/40" title={title}>
        —
      </span>
    );
  }
  return (
    <span className={cn("flex items-baseline gap-1", tone)} title={title}>
      <span>{value}</span>
      <span className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground/50">
        {label}
      </span>
    </span>
  );
}

export const DocumentCard = memo(DocumentCardImpl);
