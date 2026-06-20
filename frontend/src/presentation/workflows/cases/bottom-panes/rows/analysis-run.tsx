"use client";

import type { LucideIcon } from "lucide-react";
import {
  Bot,
  CalendarClock,
  Check,
  CheckCircle2,
  CircleDashed,
  Loader2,
  Minus,
  RotateCcw,
  User,
  X,
  XCircle,
} from "lucide-react";

import { formatDuration } from "src/application/lib/format-duration";
import { formatAnalysisRunError } from "src/domain/entities/analysis-run-error";
import type {
  AnalysisRun,
  AnalysisRunStatus,
  AnalysisRunTrigger,
} from "src/domain/entities/analysis-run";
import { DateTimeLabel } from "src/presentation/components/common/date-time-label";
import { InlineMeta } from "src/presentation/components/common/inline-meta";
import { ShortId } from "src/presentation/components/common/short-id";
import { StatusRing } from "src/presentation/components/common/status-ring";

/**
 * Status tone palette consumed by the parent pane to colorize its
 * live/idle badge. The row itself draws status with the circular ring
 * below, so we only export pill/dot/label here — icon belongs to the
 * row internals.
 */
export const STATUS_TONE: Record<
  AnalysisRunStatus,
  { label: string; pill: string; dot: string }
> = {
  RUNNING: {
    label: "running",
    pill: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
    dot: "bg-violet-500 animate-pulse",
  },
  CANCELING: {
    label: "canceling",
    pill: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500 animate-pulse",
  },
  COMPLETED: {
    label: "completed",
    pill: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  FAILED: {
    label: "failed",
    pill: "bg-red-500/10 text-red-700 dark:text-red-300",
    dot: "bg-red-500",
  },
  CANCELED: {
    label: "canceled",
    pill: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground/40",
  },
};

const STATUS_RING_COLOR: Record<AnalysisRunStatus, string> = {
  RUNNING: "text-violet-500",
  CANCELING: "text-amber-500",
  COMPLETED: "text-emerald-600 dark:text-emerald-400",
  FAILED: "text-red-600 dark:text-red-400",
  CANCELED: "text-muted-foreground",
};

// Background tonal aplicado al círculo en estados terminales — el icono
// queda recortado contra el color sin necesidad de un anillo decorativo.
const STATUS_RING_BG: Record<AnalysisRunStatus, string | undefined> = {
  RUNNING: undefined,
  CANCELING: undefined,
  COMPLETED: "bg-emerald-500/15",
  FAILED: "bg-red-500/15",
  CANCELED: "bg-muted",
};

// Glifos sin círculo intrínseco para no chocar con el bg circular.
const STATUS_ICON: Record<AnalysisRunStatus, LucideIcon> = {
  RUNNING: Loader2,
  CANCELING: Loader2,
  COMPLETED: Check,
  FAILED: X,
  CANCELED: Minus,
};

const TRIGGER_META: Record<
  AnalysisRunTrigger,
  { icon: LucideIcon; label: string; tooltip: string }
> = {
  USER: { icon: User, label: "Manual", tooltip: "Manual run" },
  RETRY: {
    icon: RotateCcw,
    label: "Reintento",
    tooltip: "Reintento automático",
  },
  SCHEDULED: {
    icon: CalendarClock,
    label: "Programado",
    tooltip: "Ejecución programada",
  },
  SYSTEM: { icon: Bot, label: "Sistema", tooltip: "Iniciado por el sistema" },
};

interface Props {
  run: AnalysisRun;
  isActive: boolean;
  isLive: boolean;
  completed: number;
  total: number;
  onSelect: (run: AnalysisRun) => void;
}

export function AnalysisRunRow({
  run,
  isActive,
  isLive,
  completed,
  total,
  onSelect,
}: Props) {
  const startedAt = run.startedAt ?? run.createdAt;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const triggerMeta = TRIGGER_META[run.trigger] ?? TRIGGER_META.USER;
  const TriggerIcon = triggerMeta.icon;

  const passed = isLive ? null : run.rulesPassed;
  const failed = isLive ? null : run.rulesFailed;
  const inconclusive = isLive ? null : run.rulesInconclusive;
  const totalRules = run.rulesTotal ?? null;

  const duration = formatDuration(run.durationMs);

  return (
    <li className="border-b border-border/40 last:border-b-0">
      <button
        type="button"
        onClick={() => onSelect(run)}
        aria-pressed={isActive}
        className={`
          group flex w-full cursor-pointer items-center gap-4 px-4 py-3
          text-left transition-colors hover:bg-muted/50
          ${isActive ? "bg-violet-500/6" : ""}
        `}
      >
        <StatusRing
          tone={STATUS_RING_COLOR[run.status]}
          bg={STATUS_RING_BG[run.status]}
          isLive={isLive}
          pct={pct}
          icon={STATUS_ICON[run.status]}
          spinIcon={run.status === "CANCELING"}
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <ShortId value={run.uuid} />
            <span className="truncate text-sm font-medium tracking-tight text-foreground">
              {triggerMeta.label}
            </span>

            {isActive ? (
              <span className="shrink-0 rounded bg-violet-500/15 px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-300">
                seleccionado
              </span>
            ) : null}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <TriggerIcon
              className="size-3.5 shrink-0 text-muted-foreground"
              aria-label={triggerMeta.tooltip}
            />
            <DateTimeLabel value={startedAt} />
            <InlineMeta>{duration}</InlineMeta>
            <InlineMeta variant="error">
              {formatAnalysisRunError(run.error)}
            </InlineMeta>
          </div>
        </div>

        <AnalysisRuleOutcome
          passed={passed}
          failed={failed}
          inconclusive={inconclusive}
          total={totalRules}
          isLive={isLive}
          liveCompleted={completed}
          liveTotal={total}
        />

        <RunStatusBadge status={run.status} />
      </button>
    </li>
  );
}

function RunStatusBadge({ status }: { status: AnalysisRunStatus }) {
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

interface RuleOutcomeProps {
  passed: number | null;
  failed: number | null;
  inconclusive: number | null;
  total: number | null;
  isLive: boolean;
  liveCompleted: number;
  liveTotal: number;
}

function AnalysisRuleOutcome(props: RuleOutcomeProps) {
  if (props.isLive) {
    return (
      <LiveOutcome completed={props.liveCompleted} total={props.liveTotal} />
    );
  }
  if (
    props.passed == null &&
    props.failed == null &&
    props.inconclusive == null
  ) {
    return <RuleCountOnly total={props.total} />;
  }
  return (
    <RuleBreakdown
      passed={props.passed}
      failed={props.failed}
      inconclusive={props.inconclusive}
    />
  );
}

function LiveOutcome({
  completed,
  total,
}: {
  completed: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  return (
    <div
      className="flex shrink-0 flex-col items-end gap-1"
      title={`Evaluando ${completed} de ${total || "?"} reglas`}
    >
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-sm font-semibold tabular-nums text-foreground/90">
          {completed}
        </span>
        <span className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground/60">
          de {total || "?"}
        </span>
      </div>
      <div
        className="h-1 w-24 overflow-hidden rounded-full bg-muted/40"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progreso del análisis"
      >
        <div
          className="h-full bg-violet-500 transition-[width] duration-500 ease-out"
          style={{ width: `${Math.max(4, pct)}%` }}
        />
      </div>
    </div>
  );
}

function RuleCountOnly({ total }: { total: number | null }) {
  if (total == null) return null;
  return (
    <div className="shrink-0 text-right">
      <div className="font-mono text-[11px] tabular-nums text-muted-foreground">
        {total} {total === 1 ? "regla" : "reglas"}
      </div>
      <div className="text-[9px] uppercase tracking-[0.16em] text-muted-foreground/50">
        sin desglose
      </div>
    </div>
  );
}

function RuleBreakdown({
  passed,
  failed,
  inconclusive,
}: {
  passed: number | null;
  failed: number | null;
  inconclusive: number | null;
}) {
  const p = passed ?? 0;
  const f = failed ?? 0;
  const i = inconclusive ?? 0;
  const safeTotal = p + f + i || 1;

  return (
    <div className="flex shrink-0 flex-col items-end gap-1.5">
      <div className="flex items-center gap-2.5 font-mono text-[11px] font-medium tabular-nums">
        <RuleCountChip
          icon={CheckCircle2}
          count={p}
          tone="text-emerald-700 dark:text-emerald-400"
          label={p === 1 ? "regla pasó" : "reglas pasaron"}
        />
        <RuleCountChip
          icon={XCircle}
          count={f}
          tone="text-red-700 dark:text-red-400"
          label={f === 1 ? "regla falló" : "reglas fallaron"}
        />
        <RuleCountChip
          icon={CircleDashed}
          count={i}
          tone="text-amber-700 dark:text-amber-400"
          label={i === 1 ? "regla indeterminada" : "reglas indeterminadas"}
        />
      </div>
      <div
        className="flex h-1 w-24 overflow-hidden rounded-full bg-muted/40"
        role="img"
        aria-label={`${p} pasaron, ${f} fallaron, ${i} indeterminadas`}
      >
        {p > 0 ? (
          <span
            className="bg-emerald-500"
            style={{ width: `${(p / safeTotal) * 100}%` }}
          />
        ) : null}
        {f > 0 ? (
          <span
            className="bg-red-500"
            style={{ width: `${(f / safeTotal) * 100}%` }}
          />
        ) : null}
        {i > 0 ? (
          <span
            className="bg-amber-500"
            style={{ width: `${(i / safeTotal) * 100}%` }}
          />
        ) : null}
      </div>
    </div>
  );
}

function RuleCountChip({
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
