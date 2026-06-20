"use client";

import { ChevronRight, PlayCircle } from "lucide-react";
import { useState } from "react";

import { useWorkflowProcessingJobsInfiniteQuery } from "@/src/application/hooks/queries/processing-jobs";
import { cn } from "@/src/application/lib/utils";
import type { WorkflowProcessingJob } from "@/src/domain/entities/workflow-processing-job";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import { ExecutionDetail } from "@/src/presentation/pipelines/executions/execution-detail";
import {
  JOB_STATUS_LABEL,
  JOB_STATUS_TONE,
  formatDateTime,
} from "@/src/presentation/pipelines/executions/phase-meta";

interface ExecutionsPanelProps {
  workflowId: string;
}

export function ExecutionsPanel({ workflowId }: ExecutionsPanelProps) {
  const [selected, setSelected] = useState<WorkflowProcessingJob | null>(null);

  const { data, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useWorkflowProcessingJobsInfiniteQuery(workflowId);

  if (selected) {
    return (
      <ExecutionDetail
        workflowId={workflowId}
        job={selected}
        onBack={() => setSelected(null)}
      />
    );
  }

  const jobs = (data?.pages ?? []).flatMap((page) => page.data);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PlayCircle className="size-4 text-primary" />
          Ejecuciones
        </CardTitle>
        <CardDescription>
          Cada corrida del pipeline. Abre una para ver su recorrido por fases y
          los datos que produjo cada una.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando ejecuciones…</p>
        ) : !jobs.length ? (
          <div className="rounded-lg border border-dashed px-4 py-10 text-center">
            <p className="text-sm font-medium">Aún no hay ejecuciones</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Procesa un archivo en este flujo para ver aquí su recorrido por el
              pipeline.
            </p>
          </div>
        ) : (
          <>
            <ul className="divide-y divide-border rounded-md ring-1 ring-inset ring-foreground/10">
              {jobs.map((job) => {
                const tone = JOB_STATUS_TONE[job.status];
                return (
                  <li key={job.setId}>
                    <button
                      type="button"
                      onClick={() => setSelected(job)}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "size-2 shrink-0 rounded-full",
                          tone.node
                        )}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">
                          {job.fileName ?? job.setId.slice(0, 8)}
                        </span>
                        <span className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                          <span className={cn("font-medium", tone.text)}>
                            {JOB_STATUS_LABEL[job.status]}
                          </span>
                          <span aria-hidden>·</span>
                          <span className="font-mono tabular-nums">
                            {formatDateTime(job.createdAt)}
                          </span>
                          {job.documentCount ? (
                            <>
                              <span aria-hidden>·</span>
                              <span className="tabular-nums">
                                {job.documentCount} docs
                              </span>
                            </>
                          ) : null}
                        </span>
                      </span>
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                    </button>
                  </li>
                );
              })}
            </ul>
            {hasNextPage && (
              <div className="mt-3 flex justify-center">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isFetchingNextPage}
                  onClick={() => fetchNextPage()}
                >
                  {isFetchingNextPage ? "Cargando…" : "Cargar más"}
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
