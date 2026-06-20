"use client";

import { ChevronDown, ChevronRight, FileText, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Fragment, useMemo, useState } from "react";

import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { useDocumentTypesQuery } from "@/src/application/hooks/queries/document-types";
import type { WorkflowProcessingJob } from "@/src/domain/entities/workflow-processing-job";
import { WorkflowProcessingJobStatus } from "@/src/domain/events/processing-job-event";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/src/presentation/components/ui/popover";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";
import { ProcessingJobStatusBadge } from "@/src/presentation/workflows/shared/processing-job-status-badge";

const INLINE_DOC_TYPE_THRESHOLD = 3;

interface LiveOverlay {
  status: WorkflowProcessingJobStatus;
  currentStep: string | null;
  progressPct: number;
}

interface ProcessingJobsTableProps {
  workflowId: string;
  sets: WorkflowProcessingJob[];
  /** Live SSE overlays keyed by setId — used to show in-flight progress. */
  liveOverlays?: Map<string, LiveOverlay>;
  onDelete?: (set: WorkflowProcessingJob) => void;
}

export function ProcessingJobsTable({
  workflowId,
  sets,
  liveOverlays,
  onDelete,
}: ProcessingJobsTableProps) {
  const router = useRouter();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const { data: docTypes } = useDocumentTypesQuery(workflowId);
  const docTypeNameById = useMemo(() => {
    const map = new Map<string, string>();
    docTypes?.forEach((t) => map.set(t.uuid, t.name));
    return map;
  }, [docTypes]);

  const navigateToDocument = (documentUuid: string) => {
    router.push(`/workflows/${workflowId}/documents/${documentUuid}`);
  };

  const rows = useMemo(() => {
    return sets.map((set) => {
      const live = liveOverlays?.get(set.setId);
      const docs = set.documents ?? [];
      const docCount = set.documentCount ?? docs.length;
      const isExpandable = docs.length > 1;
      const isOpen = expanded[set.setId] === true;
      return { set, live, docs, docCount, isExpandable, isOpen };
    });
  }, [sets, liveOverlays, expanded]);

  return (
    <Table containerClassName="overflow-visible">
      <TableHeader className="sticky top-0 z-10 bg-muted shadow-[inset_0_-1px_0_0_var(--border)]">
        <TableRow className="bg-muted hover:bg-muted">
          <TableHead className="w-10" />
          <TableHead className="text-xs uppercase tracking-wide">
            Name
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-center">
            Status
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide w-28 text-center">
            Documents
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-center">
            Document Types
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide">
            Added
          </TableHead>
          <TableHead className="w-12 text-right text-xs uppercase tracking-wide">
            <span className="sr-only">Acciones</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(({ set, live, docs, docCount, isExpandable, isOpen }) => {
          const status = live?.status ?? set.status;
          const stepLabel = live?.currentStep ?? set.currentStep ?? null;
          const progressPct = live?.progressPct;
          const docTypeNames = Array.from(
            new Set(
              docs
                .map((d) => d.documentTypeId)
                .filter((v): v is string => Boolean(v))
            )
          ).map((id) => docTypeNameById.get(id) ?? id);

          const onRowClick = () => {
            if (isExpandable) {
              setExpanded((prev) => ({
                ...prev,
                [set.setId]: !prev[set.setId],
              }));
              return;
            }
            const only = docs[0];
            if (only) navigateToDocument(only.uuid);
          };

          return (
            <Fragment key={set.setId}>
              <TableRow className="cursor-pointer" onClick={onRowClick}>
                <TableCell>
                  {isExpandable ? (
                    isOpen ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )
                  ) : null}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium underline decoration-dashed">
                      {set.fileName ?? `Set ${set.setId.slice(0, 8)}`}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex justify-center">
                    <ProcessingJobStatusBadge
                      status={status}
                      progressPct={progressPct}
                      stepLabel={stepLabel}
                      className="min-w-[100px] max-w-[150px]"
                    />
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <span className="text-sm tabular-nums">{docCount}</span>
                </TableCell>
                <TableCell>
                  {docTypeNames.length === 0 ? (
                    <div className="flex justify-center">
                      <span className="text-sm text-muted-foreground">-</span>
                    </div>
                  ) : docTypeNames.length <= INLINE_DOC_TYPE_THRESHOLD ? (
                    <div className="flex flex-wrap justify-center gap-1">
                      {docTypeNames.map((name) => (
                        <Badge key={name} variant="secondary" className="text-xs">
                          {name}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <div className="flex justify-center">
                      <Popover>
                        <PopoverTrigger
                          render={
                            <button
                              type="button"
                              aria-label={`Ver ${docTypeNames.length} document types`}
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex h-6 items-center rounded-md px-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
                            >
                              …
                            </button>
                          }
                        />
                        <PopoverContent
                          align="center"
                          className="max-w-xs"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex flex-wrap gap-1">
                            {docTypeNames.map((name) => (
                              <Badge
                                key={name}
                                variant="secondary"
                                className="text-xs"
                              >
                                {name}
                              </Badge>
                            ))}
                          </div>
                        </PopoverContent>
                      </Popover>
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {formatRelativeDate(set.createdAt)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  {onDelete ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Eliminar"
                      title="Eliminar"
                      className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(set);
                      }}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  ) : null}
                </TableCell>
              </TableRow>
              {isExpandable && isOpen
                ? docs.map((doc) => (
                    <TableRow
                      key={`${set.setId}:${doc.uuid}`}
                      className="bg-muted/20 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigateToDocument(doc.uuid);
                      }}
                    >
                      <TableCell />
                      <TableCell colSpan={6}>
                        <div className="flex items-center gap-2 pl-6">
                          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-sm underline decoration-dashed">
                            {doc.name}
                          </span>
                          {doc.documentIndex != null ? (
                            <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                              #{doc.documentIndex + 1}
                            </span>
                          ) : null}
                          {doc.pageRange ? (
                            <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                              p. {doc.pageRange.from}-{doc.pageRange.to}
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                : null}
            </Fragment>
          );
        })}
      </TableBody>
    </Table>
  );
}
