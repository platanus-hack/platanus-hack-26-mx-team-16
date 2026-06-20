"use client";

import {
  ArrowLeft,
  CheckCircle2,
  CircleDashed,
  Database,
  Loader2,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { usePhaseExecutionsQuery } from "@/src/application/hooks/queries/phase-executions";
import { cn } from "@/src/application/lib/utils";
import type { WorkflowPhaseExecution } from "@/src/domain/entities/workflow-phase-execution";
import type { WorkflowProcessingJob } from "@/src/domain/entities/workflow-processing-job";
import { isWorkflowProcessingJobTerminal } from "@/src/domain/events/processing-job-event";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  JOB_STATUS_LABEL,
  JOB_STATUS_TONE,
  PHASE_FLOW_TONE,
  PHASE_STATUS_LABEL,
  PHASE_STATUS_TONE,
  formatDateTime,
  formatDuration,
  phaseIcon,
  phaseLabel,
} from "@/src/presentation/pipelines/executions/phase-meta";
import { PipeIcon } from "@/src/presentation/pipelines/spine/icons";

interface ExecutionDetailProps {
  workflowId: string;
  job: WorkflowProcessingJob;
  onBack: () => void;
}

function StatusIcon({
  status,
  className,
}: {
  status: WorkflowPhaseExecution["status"];
  className?: string;
}) {
  if (status === "COMPLETED")
    return <CheckCircle2 className={cn("size-4 text-success-deep", className)} />;
  if (status === "FAILED")
    return <XCircle className={cn("size-4 text-destructive-deep", className)} />;
  if (status === "RUNNING")
    return (
      <Loader2 className={cn("size-4 animate-spin text-primary", className)} />
    );
  return (
    <CircleDashed className={cn("size-4 text-muted-foreground", className)} />
  );
}

export function ExecutionDetail({
  workflowId,
  job,
  onBack,
}: ExecutionDetailProps) {
  const inFlight = !isWorkflowProcessingJobTerminal(job.status);
  const { data: phases, isLoading } = usePhaseExecutionsQuery(
    workflowId,
    job.setId,
    { refetchInterval: inFlight ? 2500 : false }
  );

  const ordered = useMemo(
    () => [...(phases ?? [])].sort((a, b) => a.seq - b.seq),
    [phases]
  );

  const [selectedSeq, setSelectedSeq] = useState<number | null>(null);
  // Default selection: the failed phase if any, else the last one that ran.
  useEffect(() => {
    if (selectedSeq != null || !ordered.length) return;
    const failed = ordered.find((p) => p.status === "FAILED");
    setSelectedSeq((failed ?? ordered[ordered.length - 1]).seq);
  }, [ordered, selectedSeq]);

  const selected = ordered.find((p) => p.seq === selectedSeq) ?? null;
  const jobTone = JOB_STATUS_TONE[job.status];

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* Cabecera de la ejecución */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 rounded text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="size-4" />
          Ejecuciones
        </button>
        <span className="text-border">/</span>
        <span className="truncate text-sm font-medium">
          {job.fileName ?? job.setId.slice(0, 8)}
        </span>
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ring-1 ring-inset",
            jobTone.chip
          )}
        >
          {JOB_STATUS_LABEL[job.status]}
        </span>
        <span className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <span className="font-mono tabular-nums">
            {formatDateTime(job.createdAt)}
          </span>
          {job.documentCount ? (
            <span className="tabular-nums">{job.documentCount} docs</span>
          ) : null}
        </span>
      </div>

      {/* Split: fases (izq) · datos de la fase (der) */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden md:grid-cols-[minmax(0,20rem)_1fr]">
        {/* Grafo de fases ejecutadas (mismo lenguaje visual que el editor) */}
        <div className="min-h-0 overflow-y-auto rounded-xl border bg-muted/20">
          {isLoading ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">
              Cargando fases…
            </p>
          ) : !ordered.length ? (
            <div className="px-2 py-8 text-center">
              <p className="text-sm font-medium">Sin fases registradas</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {inFlight
                  ? "La ejecución acaba de empezar; las fases aparecerán aquí."
                  : "Esta ejecución corrió antes de registrar el detalle por fase."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col px-3 py-4">
              {ordered.map((phase, i) => (
                <div key={phase.uuid}>
                  {i > 0 && <FlowConnector />}
                  <PhaseFlowNode
                    phase={phase}
                    selected={phase.seq === selectedSeq}
                    onSelect={() => setSelectedSeq(phase.seq)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Datos de la fase seleccionada */}
        <div className="min-h-0 overflow-y-auto rounded-xl border bg-card">
          {!selected ? (
            <div className="flex h-full items-center justify-center p-6 text-center">
              <p className="text-sm text-muted-foreground">
                Elige una fase para ver los datos que produjo.
              </p>
            </div>
          ) : (
            <PhaseDataPanel phase={selected} />
          )}
        </div>
      </div>
    </div>
  );
}

/** Arrow joining two phase boxes — the vertical flow of the run (Step Functions). */
function FlowConnector() {
  return (
    <div className="flex justify-center py-1" aria-hidden>
      <svg
        width="16"
        height="22"
        viewBox="0 0 16 22"
        className="text-muted-foreground/45"
      >
        <path d="M8 1 V14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path
          d="M4 12 L8 16 L12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

/** One executed phase as a box, mirroring the editor canvas node + status tint. */
function PhaseFlowNode({
  phase,
  selected,
  onSelect,
}: {
  phase: WorkflowPhaseExecution;
  selected: boolean;
  onSelect: () => void;
}) {
  const tone = PHASE_FLOW_TONE[phase.status];
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-3 rounded-xl border bg-card px-3 py-2.5 text-left transition-shadow hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        tone.box,
        selected && "ring-2 ring-primary shadow-sm"
      )}
    >
      <span
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-lg",
          tone.iconChip
        )}
      >
        <PipeIcon name={phaseIcon(phase.phaseKind)} size={18} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">
          {phaseLabel(phase.phaseKind)}
        </span>
        <span className="block truncate font-mono text-[11px] text-muted-foreground">
          {phase.phaseId}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        <StatusIcon status={phase.status} />
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
          {formatDuration(phase.durationMs)}
        </span>
      </span>
    </button>
  );
}

function PhaseDataPanel({ phase }: { phase: WorkflowPhaseExecution }) {
  const tone = PHASE_STATUS_TONE[phase.status];
  const output = phase.outputSnapshot;
  const truncated = output && (output as { truncated?: boolean }).truncated;
  const value =
    output && "value" in output
      ? (output as { value: unknown }).value
      : truncated
        ? null
        : output;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">{phaseLabel(phase.phaseKind)}</h3>
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset",
              tone.chip
            )}
          >
            {PHASE_STATUS_LABEL[phase.status]}
          </span>
        </div>
        <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
          <div className="flex gap-1.5">
            <dt>Fase</dt>
            <dd className="font-mono text-foreground">{phase.phaseId}</dd>
          </div>
          <div className="flex gap-1.5">
            <dt>Duración</dt>
            <dd className="font-mono tabular-nums text-foreground">
              {formatDuration(phase.durationMs)}
            </dd>
          </div>
          <div className="flex gap-1.5">
            <dt>Inicio</dt>
            <dd className="font-mono text-foreground">
              {formatDateTime(phase.startedAt)}
            </dd>
          </div>
          <div className="flex gap-1.5">
            <dt>Fin</dt>
            <dd className="font-mono text-foreground">
              {formatDateTime(phase.finishedAt)}
            </dd>
          </div>
        </dl>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {phase.error ? (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-destructive-deep">
              <XCircle className="size-3.5" />
              Error
            </p>
            <pre className="overflow-auto rounded-lg border border-destructive/30 bg-destructive/5 p-3 font-mono text-xs text-destructive-deep">
              {JSON.stringify(phase.error, null, 2)}
            </pre>
          </div>
        ) : null}

        <div className={cn(phase.error && "mt-4")}>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <Database className="size-3.5" />
            Datos producidos
          </p>
          {truncated ? (
            <p className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
              Resultado demasiado grande para previsualizar (
              {String((output as { bytes?: number }).bytes ?? "")} bytes). Se
              guardó en el almacenamiento de la ejecución.
            </p>
          ) : value == null ? (
            <Badge variant="secondary" className="text-[10px]">
              sin datos
            </Badge>
          ) : (
            <pre className="overflow-auto rounded-lg border bg-muted/20 p-3 font-mono text-xs leading-relaxed">
              {JSON.stringify(value, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
