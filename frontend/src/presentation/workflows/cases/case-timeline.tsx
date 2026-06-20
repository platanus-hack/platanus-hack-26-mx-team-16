"use client";

import {
  ArrowRightLeft,
  CheckCircle2,
  FileCog,
  Flag,
  History,
  Loader2,
  type LucideIcon,
  MessageCircleQuestion,
  MessageCircleReply,
  MessageSquareText,
  PencilLine,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  SkipForward,
  Split,
  XCircle,
} from "lucide-react";

import type { SetView } from "@/src/application/hooks/use-processing-job-events";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { type CaseEvent, CaseStatus } from "@/src/domain/entities/case";
import {
  isWorkflowProcessingJobInFlight,
  WorkflowProcessingJobStatus,
} from "@/src/domain/events/processing-job-event";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Button } from "@/src/presentation/components/ui/button";
import { caseStatusConfig } from "./case-status-config";

interface Props {
  events: CaseEvent[];
  /** Re-IA 2026-06: runs técnicos del caso, intercalados en la actividad. */
  jobs?: SetView[];
  onRetryJob?: (processingJobId: string) => void;
  retryingJobIds?: Set<string>;
}

function statusLabel(value: unknown): string {
  if (
    typeof value === "string" &&
    (Object.values(CaseStatus) as string[]).includes(value)
  ) {
    return caseStatusConfig[value as CaseStatus].label;
  }
  return String(value ?? "—");
}

interface EventPresentation {
  icon: LucideIcon;
  iconClassName: string;
  title: string;
  detail?: string;
}

/** E5 · sufijo legible del stage de revisión multinivel. */
function stageSuffix(payload: Record<string, unknown>): string {
  const stage = typeof payload.stage === "string" ? payload.stage : null;
  if (stage === "review_l1") return " (L1)";
  if (stage === "review_l2") return " (L2)";
  return "";
}

/** Descripción legible en español por tipo de case_event. */
function presentEvent(event: CaseEvent): EventPresentation {
  const payload = event.payload ?? {};
  switch (event.type) {
    case "status.changed": {
      const reason = typeof payload.reason === "string" ? payload.reason : "";
      return {
        icon: ArrowRightLeft,
        iconClassName: "text-muted-foreground",
        title: `Pasó de «${statusLabel(payload.from)}» a «${statusLabel(payload.to)}»`,
        detail: reason || undefined,
      };
    }
    case "ready":
      return {
        icon: Flag,
        iconClassName: "text-primary",
        title: payload.force
          ? "Caso marcado como listo (forzado)"
          : "Caso marcado como listo",
      };
    case "review.approved":
      return {
        icon: CheckCircle2,
        iconClassName: "text-emerald-600",
        title: `Revisión aprobada${stageSuffix(payload)}`,
        detail:
          typeof payload.comment === "string" && payload.comment
            ? payload.comment
            : undefined,
      };
    case "review.rejected":
      return {
        icon: XCircle,
        iconClassName: "text-red-600",
        title: `Revisión rechazada${stageSuffix(payload)}`,
        detail:
          typeof payload.comment === "string" && payload.comment
            ? payload.comment
            : undefined,
      };
    case "review.skipped":
      return {
        icon: SkipForward,
        iconClassName: "text-muted-foreground",
        title: `Revisión omitida (paso directo)${stageSuffix(payload)}`,
      };
    case "clarification.requested": {
      const items = Array.isArray(payload.items) ? payload.items.length : 0;
      return {
        icon: MessageCircleQuestion,
        iconClassName: "text-amber-600",
        title: "Aclaración solicitada",
        detail:
          items > 0
            ? `${items} ${items === 1 ? "campo" : "campos"} con baja confianza`
            : undefined,
      };
    }
    case "clarification.resolved":
      return {
        icon: MessageCircleReply,
        iconClassName: "text-emerald-600",
        title: "Aclaración resuelta",
      };
    // ── E5 · fan-out, revisión multinivel y bench ──────────────────────
    case "comment.added":
      return {
        icon: MessageSquareText,
        iconClassName: "text-primary",
        title: "Comentario",
        detail:
          typeof payload.body === "string" && payload.body
            ? payload.body
            : undefined,
      };
    case "case.split": {
      const total =
        typeof payload.total === "number"
          ? payload.total
          : Array.isArray(payload.children)
            ? payload.children.length
            : 0;
      return {
        icon: Split,
        iconClassName: "text-primary",
        title: `Caso dividido en ${total} ${total === 1 ? "caso derivado" : "casos derivados"}`,
      };
    }
    case "children.completed": {
      const total = typeof payload.total === "number" ? payload.total : null;
      return {
        icon: CheckCircle2,
        iconClassName: "text-emerald-600",
        title: "Todos los casos derivados terminaron",
        detail: total !== null ? `${total} casos` : undefined,
      };
    }
    case "analysis.rerun":
      return {
        icon: RefreshCw,
        iconClassName: "text-muted-foreground",
        title: "Análisis re-ejecutado tras correcciones",
      };
    case "field.corrected": {
      const field =
        typeof payload.fieldPath === "string" ? payload.fieldPath : null;
      return {
        icon: PencilLine,
        iconClassName: "text-amber-600",
        title: field ? `Campo corregido: ${field}` : "Campo corregido",
      };
    }
    case "field.verified": {
      const field =
        typeof payload.fieldPath === "string" ? payload.fieldPath : null;
      return {
        icon: ShieldCheck,
        iconClassName: "text-emerald-600",
        title: field ? `Campo verificado: ${field}` : "Campo verificado",
      };
    }
    default:
      return {
        icon: History,
        iconClassName: "text-muted-foreground",
        title: event.type,
      };
  }
}

/** Re-IA 2026-06: presentación de un run técnico dentro de la actividad. */
function presentJob(job: SetView): {
  icon: LucideIcon;
  iconClassName: string;
  title: string;
  live: boolean;
} {
  const fileLabel = job.fileName ?? `run ${job.setId.slice(0, 8)}`;
  if (isWorkflowProcessingJobInFlight(job.status)) {
    return {
      icon: Loader2,
      iconClassName: "text-primary animate-spin motion-reduce:animate-none",
      title: `Procesando «${fileLabel}»`,
      live: true,
    };
  }
  if (job.status === WorkflowProcessingJobStatus.FAILED) {
    return {
      icon: XCircle,
      iconClassName: "text-red-600",
      title: `Procesamiento de «${fileLabel}» falló`,
      live: false,
    };
  }
  return {
    icon: FileCog,
    iconClassName: "text-emerald-600",
    title: `Procesado «${fileLabel}»`,
    live: false,
  };
}

function timestampNode(value: string | null) {
  if (!value) return null;
  return (
    <>
      <span className="text-xs text-muted-foreground" title={value}>
        {formatRelativeDate(value)}
      </span>
      <span className="font-mono text-xs text-muted-foreground/80">
        {new Date(value).toLocaleString("es", {
          dateStyle: "medium",
          timeStyle: "short",
        })}
      </span>
    </>
  );
}

type TimelineEntry =
  | { kind: "event"; key: string; ts: string; event: CaseEvent }
  | { kind: "job"; key: string; ts: string; job: SetView };

/**
 * E4 · Timeline de eventos del caso (case_events, desc) + Re-IA 2026-06:
 * los runs técnicos de procesamiento se intercalan como entradas propias
 * (estado, causa del fallo y «Reintentar» inline) — antes vivían en un
 * drawer aparte que contradecía a esta vista. Tailwind puro.
 * `completeness.evaluated` se omite (ruido operativo, no narrativo).
 */
export function CaseTimeline({
  events,
  jobs = [],
  onRetryJob,
  retryingJobIds,
}: Props) {
  const entries: TimelineEntry[] = [
    ...events
      .filter((e) => e.type !== "completeness.evaluated")
      .map((event) => ({
        kind: "event" as const,
        key: `event-${event.uuid}`,
        ts: event.createdAt ?? "",
        event,
      })),
    ...jobs.map((job) => ({
      kind: "job" as const,
      key: `job-${job.setId}`,
      ts: job.startedAt ?? job.createdAt ?? "",
      job,
    })),
  ].sort((a, b) => b.ts.localeCompare(a.ts));

  if (entries.length === 0) {
    return (
      <div className="flex h-full items-center justify-center py-12">
        <EmptyState
          icon={History}
          title="Sin actividad todavía"
          description="Aquí verás el historial del expediente: procesamiento de archivos, cambios de estado, revisiones y aclaraciones."
        />
      </div>
    );
  }

  return (
    <ol className="relative ml-3 space-y-6 border-l border-border py-2 pl-6">
      {entries.map((entry) => {
        if (entry.kind === "job") {
          const { job } = entry;
          const { icon: Icon, iconClassName, title, live } = presentJob(job);
          const isRetrying = retryingJobIds?.has(job.setId) ?? false;
          return (
            <li key={entry.key} className="relative">
              <span className="absolute -left-[31px] top-0.5 flex size-5 items-center justify-center rounded-full bg-card ring-1 ring-foreground/10">
                <Icon className={`size-3 ${iconClassName}`} />
              </span>
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <p className="text-sm font-medium">{title}</p>
                {live && (
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide text-primary">
                    <span className="size-1.5 rounded-full bg-primary animate-pulse motion-reduce:animate-none" />
                    live
                  </span>
                )}
                {timestampNode(entry.ts || null)}
              </div>
              {job.status === WorkflowProcessingJobStatus.FAILED && (
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <p className="max-w-prose text-sm text-red-700 dark:text-red-300">
                    {job.error
                      ? `${job.error.message} (${job.error.code} · ${job.error.sourceStep})`
                      : "El procesamiento falló sin detalle de causa."}
                  </p>
                  {onRetryJob && (
                    <Button
                      variant="outline"
                      size="xs"
                      disabled={isRetrying}
                      onClick={() => onRetryJob(job.setId)}
                    >
                      <RotateCcw className="mr-1 h-3 w-3" />
                      {isRetrying ? "Reintentando…" : "Reintentar"}
                    </Button>
                  )}
                </div>
              )}
            </li>
          );
        }

        const { event } = entry;
        const {
          icon: Icon,
          iconClassName,
          title,
          detail,
        } = presentEvent(event);
        return (
          <li key={entry.key} className="relative">
            <span className="absolute -left-[31px] top-0.5 flex size-5 items-center justify-center rounded-full bg-card ring-1 ring-foreground/10">
              <Icon className={`size-3 ${iconClassName}`} />
            </span>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
              <p className="text-sm font-medium">{title}</p>
              {timestampNode(event.createdAt)}
            </div>
            {detail && (
              <p className="mt-0.5 max-w-prose text-sm text-muted-foreground">
                {detail}
              </p>
            )}
            {event.actor && (
              <p className="mt-0.5 text-xs text-muted-foreground">
                por <span className="font-medium">{event.actor}</span>
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
