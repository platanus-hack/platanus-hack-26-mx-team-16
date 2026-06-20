"use client";

import { ShieldCheck } from "lucide-react";
import { memo } from "react";

import type { AnalysisRun } from "src/domain/entities/analysis-run";
import { PageContent } from "src/presentation/components/common/page-content";
import {
  AnalysisRunRow,
  STATUS_TONE,
} from "src/presentation/workflows/cases/bottom-panes/rows/analysis-run";

interface Props {
  history: AnalysisRun[];
  activeRun: AnalysisRun | null;
  isLive: boolean;
  isHydrated: boolean;
  completed: number;
  total: number;
  onSelect: (run: AnalysisRun) => void;
}

const IDLE_TONE = {
  pill: "bg-muted text-muted-foreground",
  dot: "bg-muted-foreground/40",
  label: "idle",
} as const;

function LiveAnalysisRunsPaneImpl({
  history,
  activeRun,
  isLive,
  isHydrated,
  completed,
  total,
  onSelect,
}: Props) {
  const liveTone = isLive ? STATUS_TONE.RUNNING : IDLE_TONE;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  const summary = `${history.length} ${history.length === 1 ? "run" : "runs"}${
    isLive ? " · 1 en curso" : ""
  }`;

  return (
    <>
      <PageContent.LiveBottomPane.Header
        icon={ShieldCheck}
        title="Histórico de Análisis"
        label={summary}
      >
        {isLive ? (
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground tabular-nums">
            {completed}/{total || "?"} · {pct}%
          </span>
        ) : null}
        <span
          className={`
            inline-flex items-center gap-1.5 rounded-full px-2 py-0.5
            font-mono text-[10px] uppercase tracking-[0.18em]
            ${liveTone.pill}
          `}
        >
          <span
            className={`
              inline-block h-1.5 w-1.5 rounded-full
              ${liveTone.dot}
            `}
          />
          {liveTone.label}
        </span>
      </PageContent.LiveBottomPane.Header>

      {isLive ? (
        <div className="relative h-0.5 w-full shrink-0 bg-border/40">
          <div
            className="absolute inset-y-0 left-0 bg-violet-500 transition-[width] duration-500 ease-out"
            style={{ width: `${Math.max(8, pct)}%` }}
          />
        </div>
      ) : null}

      <PageContent.LiveBottomPane.Content className="pb-14">
        {!isHydrated ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Cargando ejecuciones…
          </div>
        ) : history.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Aún no se han ejecutado análisis.
          </div>
        ) : (
          <ul className="flex flex-col">
            {history.map((run) => (
              <AnalysisRunRow
                key={run.uuid}
                run={run}
                isActive={activeRun?.uuid === run.uuid}
                isLive={activeRun?.uuid === run.uuid && isLive}
                completed={completed}
                total={total}
                onSelect={onSelect}
              />
            ))}
          </ul>
        )}
      </PageContent.LiveBottomPane.Content>
    </>
  );
}

export const LiveAnalysisRunsPane = memo(LiveAnalysisRunsPaneImpl);
