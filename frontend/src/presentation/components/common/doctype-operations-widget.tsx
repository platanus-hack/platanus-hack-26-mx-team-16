"use client";

import { CheckCircle2, ChevronDown, ChevronUp, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/src/application/lib/utils";
import { Spinner } from "@/src/presentation/components/ui/spinner";
import {
  useBackgroundTasksStore,
  BackgroundTaskStatus,
  type BackgroundTask,
} from "@/src/application/stores/background-tasks-store";
import { useDoctypeEvents } from "@/src/application/hooks/use-doctype-events";
import { useDoctypeTaskActions } from "@/src/application/hooks/use-doctype-task-actions";

const AUTO_REMOVE_MS = 3000;

// Renders nothing — just keeps the SSE open for one doctype while the detail
// view is not mounted (e.g. user is on the workflow overview tab).
// When the detail view IS mounted it runs its own useDoctypeEvents; both
// receiving the same event is fine because completeTask / errorTask are idempotent.
function DoctypeEventListener({ doctypeId }: { doctypeId: string }) {
  const { completeTaskFor, errorTaskFor } = useDoctypeTaskActions(doctypeId);

  useDoctypeEvents(doctypeId, {
    onSampleTextExtracted: () => completeTaskFor("doctype-text"),
    onSampleTextFailed: errorTaskFor(
      "doctype-text",
      "Error al extraer el texto"
    ),
    onFieldsSuggested: () => completeTaskFor("doctype-fields"),
    onFieldsSuggestionFailed: errorTaskFor(
      "doctype-fields",
      "Field generation failed"
    ),
  });
  return null;
}

function TaskRow({ task }: { task: BackgroundTask }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className="mt-0.5 shrink-0">
        {task.status === BackgroundTaskStatus.Pending && <Spinner size="xs" />}
        {task.status === BackgroundTaskStatus.Completed && (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        )}
        {task.status === BackgroundTaskStatus.Error && (
          <XCircle className="h-3.5 w-3.5 text-destructive" />
        )}
      </div>
      <div className="flex min-w-0 flex-col gap-0.5">
        {task.entityLabel && (
          <span className="text-[11px] text-muted-foreground truncate leading-tight">
            {task.entityLabel}
          </span>
        )}
        <span className="text-xs font-medium leading-tight">{task.label}</span>
        {task.status === BackgroundTaskStatus.Completed && (
          <span className="text-xs text-muted-foreground">Completado</span>
        )}
        {task.status === BackgroundTaskStatus.Error && task.errorMessage && (
          <span className="text-xs text-destructive">{task.errorMessage}</span>
        )}
      </div>
    </div>
  );
}

export function DoctypeOperationsWidget() {
  const tasks = useBackgroundTasksStore((s) => s.tasks);
  const removeTask = useBackgroundTasksStore((s) => s.removeTask);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const timers = tasks
      .filter((t) => t.status !== BackgroundTaskStatus.Pending)
      .map((t) => setTimeout(() => removeTask(t.id), AUTO_REMOVE_MS));
    return () => timers.forEach(clearTimeout);
  }, [tasks, removeTask]);

  // One listener per distinct doctype that still has pending tasks.
  // Key includes the latest task ID so the component remounts (and SSE
  // reconnects) when a new task starts for a doctype whose previous SSE
  // closed after a terminal event.
  const pendingDoctypeMap = tasks
    .filter((t) => t.status === BackgroundTaskStatus.Pending)
    .reduce((map, t) => {
      map.set(t.entityId, t.id);
      return map;
    }, new Map<string, string>());

  if (tasks.length === 0) return null;

  const lastTask = tasks[tasks.length - 1];
  const reversedTasks = [...tasks].reverse();

  return (
    <>
      {/* Background SSE listeners — invisible, one per pending doctype */}
      {[...pendingDoctypeMap.entries()].map(([doctypeId, latestTaskId]) => (
        <DoctypeEventListener
          key={`${doctypeId}-${latestTaskId}`}
          doctypeId={doctypeId}
        />
      ))}

      <div
        className={cn(
          "fixed bottom-4 right-4 z-50 min-w-72 max-w-sm overflow-hidden",
          "rounded-lg border bg-background shadow-lg"
        )}
      >
        {/* Summary row — always visible, acts as expand/collapse toggle */}
        <button
          type="button"
          onClick={() => setIsExpanded((e) => !e)}
          className="flex w-full items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors"
        >
          <div className="shrink-0">
            {lastTask.status === "pending" && <Spinner size="xs" />}
            {lastTask.status === "completed" && (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            )}
            {lastTask.status === "error" && (
              <XCircle className="h-3.5 w-3.5 text-destructive" />
            )}
          </div>

          <div className="flex min-w-0 flex-1 flex-col text-left">
            {lastTask.entityLabel && (
              <span className="text-[11px] text-muted-foreground truncate leading-tight">
                {lastTask.entityLabel}
              </span>
            )}
            <span className="text-xs font-medium leading-tight truncate">
              {lastTask.label}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            {tasks.length > 1 && (
              <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
                {tasks.length}
              </span>
            )}
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </div>
        </button>

        {/* Expanded task list */}
        {isExpanded && (
          <div className="border-t divide-y max-h-64 overflow-y-auto">
            {reversedTasks.map((task) => (
              <TaskRow key={task.id} task={task} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
