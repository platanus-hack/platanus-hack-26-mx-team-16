"use client";

import { FileStack } from "lucide-react";
import { memo, useMemo } from "react";

import {
  type DocumentView,
  type SetView,
} from "src/application/hooks/use-processing-job-events";
import { WorkflowProcessingJobStatus } from "src/domain/events/processing-job-event";
import type { ConnectionState } from "src/infrastructure/http/sse";
import { PageContent } from "src/presentation/components/common/page-content";
import { WorkflowProcessingJobRow } from "./rows/workflow-processing-job";

interface Props {
  sets: SetView[];
  documents: DocumentView[];
  isHydrated: boolean;
  connectionState: ConnectionState;
}

// Static class strings so Tailwind picks them up at build time.
const CONNECTION_BADGE: Record<
  ConnectionState,
  { label: string; pill: string; dot: string }
> = {
  connected: {
    label: "live",
    pill: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    dot: "bg-emerald-500 animate-pulse",
  },
  connecting: {
    label: "connecting",
    pill: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500 animate-pulse",
  },
  reconnecting: {
    label: "reconnecting",
    pill: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500 animate-pulse",
  },
  idle: {
    label: "offline",
    pill: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground/40",
  },
};

function LiveWorkflowProcessingJobsPaneImpl({
  sets,
  documents,
  isHydrated,
  connectionState,
}: Props) {
  const docsBySet = useMemo(() => {
    const map = new Map<string, DocumentView[]>();
    for (const d of documents) {
      const key = d.processingJobId ?? "__unassigned__";
      const list = map.get(key);
      if (list) list.push(d);
      else map.set(key, [d]);
    }
    return map;
  }, [documents]);

  const activeCount = sets.filter(
    (s) => s.status === WorkflowProcessingJobStatus.PROCESSING
  ).length;

  const summary = `${sets.length} ${sets.length === 1 ? "set" : "sets"}${
    activeCount > 0 ? ` · ${activeCount} en curso` : ""
  }`;

  const badge = CONNECTION_BADGE[connectionState];

  return (
    <>
      <PageContent.LiveBottomPane.Header
        icon={FileStack}
        title="Documentos Procesados"
        label={summary}
      >
        <span
          className={`
            inline-flex items-center gap-1.5 rounded-full px-2 py-0.5
            font-mono text-[10px] uppercase tracking-[0.18em]
            ${badge.pill}
          `}
        >
          <span
            className={`
              inline-block h-1.5 w-1.5 rounded-full
              ${badge.dot}
            `}
          />
          {badge.label}
        </span>
      </PageContent.LiveBottomPane.Header>

      <PageContent.LiveBottomPane.Content className="pb-14">
        {!isHydrated ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Cargando estado de procesamiento…
          </div>
        ) : sets.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            No hay cargas activas.
          </div>
        ) : (
          <ul className="flex flex-col">
            {sets.map((set) => (
              <WorkflowProcessingJobRow
                key={set.setId}
                set={set}
                documents={docsBySet.get(set.setId) ?? []}
              />
            ))}
          </ul>
        )}
      </PageContent.LiveBottomPane.Content>
    </>
  );
}

export const LiveWorkflowProcessingJobsPane = memo(
  LiveWorkflowProcessingJobsPaneImpl
);
