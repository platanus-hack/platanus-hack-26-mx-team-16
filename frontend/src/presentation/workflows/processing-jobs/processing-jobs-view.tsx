"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ChevronDown,
  Code,
  FileText,
  FilterX,
  Info,
  Mail,
  Upload,
  XCircle,
} from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDocumentTypesQuery } from "@/src/application/hooks/queries/document-types";
import { queryKeys } from "@/src/application/hooks/queries/keys";
import {
  useDeleteWorkflowProcessingJobMutation,
  useWorkflowProcessingJobsInfiniteQuery,
} from "@/src/application/hooks/queries/processing-jobs";
import {
  useUpdateWorkflowMutation,
  useWorkflowQuery,
} from "@/src/application/hooks/queries/workflows";
import { useAutoHideScrollbar } from "@/src/application/hooks/use-auto-hide-scrollbar";
import { useDebouncedState } from "@/src/application/hooks/use-debounced-state";
import { useInfiniteScroll } from "@/src/application/hooks/use-infinite-scroll";
import { useProcessingJobEvents } from "@/src/application/hooks/use-processing-job-events";
import { cn } from "@/src/application/lib/utils";
import { DocumentStatus } from "@/src/domain/entities/document";
import type { WorkflowProcessingJob } from "@/src/domain/entities/workflow-processing-job";
import { WorkflowProcessingJobStatus } from "@/src/domain/events/processing-job-event";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { EditableInlineName } from "@/src/presentation/components/common/editable-inline-name";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import {
  type FilterOption,
  MultiSelectFilter,
} from "@/src/presentation/components/common/multi-select-filter";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { SearchInputFilter } from "@/src/presentation/components/common/search-input-filter";
import { Show } from "@/src/presentation/components/common/show";
import { DateRangeFilter } from "@/src/presentation/components/filters/date-range-filter";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  FullPageSpinner,
  Spinner,
} from "@/src/presentation/components/ui/spinner";
import { FileUploadButton } from "../shared/file-upload-button";
import { ProcessingJobsTable } from "./tables/processing-jobs-table";

type DocumentFilterTab = "all" | DocumentStatus;

function WorkflowProcessingJobsEmpty({
  filter,
  workflow,
  workflowId,
  docTypes,
  onDispatched,
  onUploadEmail,
  onUploadApi,
}: {
  filter: DocumentFilterTab;
  workflow: { selectedDocTypes: string[] } | undefined;
  workflowId: string;
  docTypes: Array<{ uuid: string; name: string }>;
  onDispatched: (setId: string) => void;
  onUploadEmail: () => void;
  onUploadApi: () => void;
}) {
  const t = useTranslations("Documents");

  if (filter === DocumentStatus.ARCHIVED) {
    return (
      <div className="flex h-full items-center justify-center p-12">
        <div className="flex flex-col items-center space-y-4 max-w-md text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted/50">
            <Archive className="h-10 w-10 text-muted-foreground/60" />
          </div>
          <h3 className="text-xl font-semibold">{t("archived.title")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("archived.description")}
          </p>
        </div>
      </div>
    );
  }

  if (filter === DocumentStatus.REJECTED) {
    return (
      <div className="flex h-full items-center justify-center p-12">
        <div className="flex flex-col items-center space-y-4 max-w-md text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted/50">
            <XCircle className="h-10 w-10 text-muted-foreground/60" />
          </div>
          <h3 className="text-xl font-semibold">{t("rejected.title")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("rejected.description")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="flex items-center justify-center w-full h-full border-2 border-dashed border-border rounded-lg p-12">
        <div className="flex flex-col items-center space-y-8 max-w-2xl">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted/50 border-2 border-dashed border-muted-foreground/20">
            <Upload className="h-10 w-10 text-muted-foreground/40" />
          </div>
          <div className="flex flex-col items-center space-y-3 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">
              {t("empty.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("empty.description")}
            </p>
          </div>
          <FileUploadButton
            workflowId={workflowId}
            onDispatched={onDispatched}
            label={t("chooseFiles")}
          />
          {workflow && workflow.selectedDocTypes.length > 0 && (
            <div className="flex flex-col items-center space-y-3">
              <p className="text-sm text-muted-foreground">
                {t("empty.willBeClassified")}
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {workflow.selectedDocTypes.map((docTypeId) => {
                  const name =
                    docTypes.find((dt) => dt.uuid === docTypeId)?.name ??
                    docTypeId;
                  return (
                    <Badge
                      key={docTypeId}
                      variant="outline"
                      className="gap-1.5 font-normal text-sm px-3 py-1"
                    >
                      <FileText className="h-3.5 w-3.5" />
                      {name}
                    </Badge>
                  );
                })}
              </div>
            </div>
          )}
          <div className="flex items-center gap-4 pt-4">
            <Button
              variant="link"
              onClick={onUploadEmail}
              className="gap-2 h-10 text-blue-500 hover:text-blue-600"
            >
              <Mail className="h-4 w-4" />
              {t("empty.uploadEmail")}
            </Button>
            <Button
              variant="link"
              onClick={onUploadApi}
              className="gap-2 h-10 text-blue-500 hover:text-blue-600"
            >
              <Code className="h-4 w-4" />
              {t("empty.uploadApi")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function WorkflowProcessingJobsView() {
  const t = useTranslations("Documents");
  const tNav = useTranslations("Nav");
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const wfSlug = params.wfSlug as string;

  const [optimisticSets, setOptimisticSets] = useState<string[]>([]);

  const { data: workflow, isLoading: isLoadingWorkflow } =
    useWorkflowQuery(wfSlug);
  const updateWorkflowMutation = useUpdateWorkflowMutation();
  // E7 · F4: `workflow_type` murió ⇒ la vista `/documents` es SIEMPRE la tabla
  // técnica de runs (processing-jobs) para todo workflow. La antigua vista dual de
  // documentos sueltos por tipo se retiró (era inalcanzable).

  const [selectedStatuses, setSelectedStatuses] = useState<
    WorkflowProcessingJobStatus[]
  >([]);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([]);
  const [searchTerm, debouncedSearch, handleSearchChange] = useDebouncedState(
    searchParams.get("search") ?? ""
  );
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const statusOptions: FilterOption<WorkflowProcessingJobStatus>[] = useMemo(
    () => [
      {
        label: t("status.pending"),
        value: WorkflowProcessingJobStatus.PENDING,
      },
      {
        label: t("status.running"),
        value: WorkflowProcessingJobStatus.RUNNING,
      },
      {
        label: t("status.processing"),
        value: WorkflowProcessingJobStatus.PROCESSING,
      },
      {
        label: t("status.completed"),
        value: WorkflowProcessingJobStatus.COMPLETED,
      },
      {
        label: t("status.partial"),
        value: WorkflowProcessingJobStatus.PARTIAL,
      },
      {
        label: t("status.failed"),
        value: WorkflowProcessingJobStatus.FAILED,
      },
    ],
    [t]
  );

  const backendStatusMap: Record<WorkflowProcessingJobStatus, string> = {
    [WorkflowProcessingJobStatus.PENDING]: "PENDING",
    [WorkflowProcessingJobStatus.RUNNING]: "RUNNING",
    [WorkflowProcessingJobStatus.PROCESSING]: "PROCESSING",
    [WorkflowProcessingJobStatus.COMPLETED]: "COMPLETED",
    [WorkflowProcessingJobStatus.PARTIAL]: "PARTIAL",
    [WorkflowProcessingJobStatus.FAILED]: "FAILED",
  };

  const activeFilters = useMemo(() => {
    const f: Record<string, string> = {};
    if (debouncedSearch) f.search = debouncedSearch;
    if (selectedStatuses.length > 0) {
      f.statuses = selectedStatuses.map((s) => backendStatusMap[s]).join(",");
    }
    if (selectedDocTypes.length > 0)
      f.documentTypes = selectedDocTypes.join(",");
    if (dateFrom) f.dateFrom = dateFrom;
    if (dateTo) f.dateTo = dateTo;
    return f;
  }, [debouncedSearch, selectedStatuses, selectedDocTypes, dateFrom, dateTo]);

  const { data: docTypes = [], isLoading: isLoadingDocTypes } =
    useDocumentTypesQuery(wfSlug);

  const {
    data: paginatedSets,
    fetchNextPage,
    hasNextPage,
    isFetching: isFetchingSets,
    isFetchingNextPage,
  } = useWorkflowProcessingJobsInfiniteQuery(wfSlug, activeFilters);

  const processingJobs = useMemo(
    () => paginatedSets?.pages.flatMap((p) => p.data) ?? [],
    [paginatedSets]
  );

  const isLoading =
    isLoadingWorkflow || (isFetchingSets && !isFetchingNextPage);

  const { sets, documents: liveDocuments } = useProcessingJobEvents({
    workflowId: wfSlug,
  });

  const liveOverlays = useMemo(() => {
    const map = new Map<
      string,
      {
        status: WorkflowProcessingJobStatus;
        currentStep: string | null;
        progressPct: number;
      }
    >();
    for (const s of sets) {
      map.set(s.setId, {
        status: s.status,
        currentStep: s.currentStep ?? null,
        progressPct: s.progressPct,
      });
    }
    return map;
  }, [sets]);

  const queryClient = useQueryClient();
  const refreshLists = useCallback(() => {
    void queryClient.refetchQueries({
      queryKey: queryKeys.processingJobs.paginated(wfSlug),
      type: "active",
    });
    void queryClient.refetchQueries({
      queryKey: queryKeys.processingJobs.all(wfSlug),
      type: "active",
    });
    void queryClient.refetchQueries({
      queryKey: queryKeys.documents.all(wfSlug),
      type: "active",
    });
  }, [queryClient, wfSlug]);

  const refetchedTerminalSetIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    const terminal = new Set<WorkflowProcessingJobStatus>([
      WorkflowProcessingJobStatus.COMPLETED,
      WorkflowProcessingJobStatus.PARTIAL,
      WorkflowProcessingJobStatus.FAILED,
    ]);
    let triggered = false;
    for (const s of sets) {
      if (
        terminal.has(s.status) &&
        !refetchedTerminalSetIds.current.has(s.setId)
      ) {
        refetchedTerminalSetIds.current.add(s.setId);
        triggered = true;
      }
    }
    if (!triggered) return;
    refreshLists();
    const timer = setTimeout(refreshLists, 600);
    return () => clearTimeout(timer);
  }, [sets, refreshLists]);

  const seenLiveDocIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    let triggered = false;
    for (const d of liveDocuments) {
      if (!seenLiveDocIds.current.has(d.documentId)) {
        seenLiveDocIds.current.add(d.documentId);
        triggered = true;
      }
    }
    if (triggered) refreshLists();
  }, [liveDocuments, refreshLists]);

  const mergedSets = useMemo<WorkflowProcessingJob[]>(() => {
    const persistedIds = new Set(processingJobs.map((s) => s.setId));
    const hasDateFilter = !!(dateFrom || dateTo);
    const liveOnly: WorkflowProcessingJob[] =
      debouncedSearch || hasDateFilter
        ? []
        : sets
            .filter((s) => !persistedIds.has(s.setId))
            .filter(
              (s) =>
                selectedStatuses.length === 0 ||
                selectedStatuses.includes(s.status)
            )
            .map((s) => ({
              setId: s.setId,
              temporalWorkflowId: s.setId,
              workflowId: wfSlug,
              fileId: "",
              status: s.status,
              currentStep: s.currentStep,
              lastSeq: s.lastSeq ?? 0,
            }));
    const liveIds = new Set(sets.map((s) => s.setId));
    const optimisticOnly: WorkflowProcessingJob[] =
      debouncedSearch ||
      hasDateFilter ||
      (selectedStatuses.length > 0 &&
        !selectedStatuses.includes(WorkflowProcessingJobStatus.PENDING))
        ? []
        : optimisticSets
            .filter((id) => !persistedIds.has(id) && !liveIds.has(id))
            .map((setId) => ({
              setId,
              temporalWorkflowId: setId,
              workflowId: wfSlug,
              fileId: "",
              status: WorkflowProcessingJobStatus.PENDING,
              lastSeq: 0,
            }));
    return [...optimisticOnly, ...liveOnly, ...processingJobs];
  }, [
    processingJobs,
    sets,
    optimisticSets,
    wfSlug,
    selectedStatuses,
    debouncedSearch,
    dateFrom,
    dateTo,
  ]);

  const handleDispatched = (setId: string) => {
    setOptimisticSets((prev) =>
      prev.includes(setId) ? prev : [...prev, setId]
    );
    queryClient.invalidateQueries({
      queryKey: queryKeys.processingJobs.paginated(wfSlug),
    });
  };

  const [setToDelete, setSetToDelete] = useState<WorkflowProcessingJob | null>(
    null
  );
  const [deletedSetIds, setDeletedSetIds] = useState<Set<string>>(
    () => new Set()
  );
  const deleteMutation = useDeleteWorkflowProcessingJobMutation(wfSlug);

  const confirmDeleteSet = async () => {
    if (!setToDelete) return;
    const targetId = setToDelete.setId;
    setSetToDelete(null);
    setOptimisticSets((prev) => prev.filter((id) => id !== targetId));
    setDeletedSetIds((prev) => {
      const next = new Set(prev);
      next.add(targetId);
      return next;
    });
    await deleteMutation.mutateAsync(targetId);
  };

  const scrollRef = useInfiniteScroll(
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  );
  useAutoHideScrollbar(scrollRef);

  if (isLoading && mergedSets.length === 0) {
    return <FullPageSpinner />;
  }

  const hasConfirmedDocuments = false;
  const hasActiveFilters = Object.keys(activeFilters).length > 0;
  const showEmptyState =
    mergedSets.length === 0 && !isFetchingSets && !hasActiveFilters;

  const deleteSetName =
    setToDelete?.fileName ??
    t("deleteSetFallback", {
      id: setToDelete?.setId.slice(0, 8) ?? "",
    });

  return (
    <PageContent>
      <PageContent.Header
        icon={FileText}
        title={
          workflow ? (
            <h1 className="truncate text-xl font-semibold leading-tight tracking-tight">
              <EditableInlineName
                value={workflow.name}
                onSave={async (nextName) => {
                  await updateWorkflowMutation.mutateAsync({
                    uuid: workflow.uuid,
                    payload: { name: nextName },
                  });
                }}
                maxWidthClassName="max-w-[42ch]"
              />
            </h1>
          ) : (
            tNav("workflows")
          )
        }
        subtitle={t("subtitle")}
        showBack
        onBack={() => router.push("/workflows")}
        actions={
          <FileUploadButton
            workflowId={wfSlug}
            onDispatched={handleDispatched}
            label={t("uploadLabel")}
          />
        }
      />
      <PageContent.Body scroll={false}>
        <Show
          when={!showEmptyState}
          fallback={
            <WorkflowProcessingJobsEmpty
              filter="all"
              workflow={workflow}
              workflowId={wfSlug}
              docTypes={docTypes}
              onDispatched={handleDispatched}
              onUploadEmail={() => console.log("Upload via email")}
              onUploadApi={() => console.log("Upload via API")}
            />
          }
        >
          <div className="flex flex-1 min-h-0 flex-col overflow-hidden rounded-lg border">
            <div className="px-2 py-1 border-b shrink-0">
              <div className="flex items-center justify-between gap-4">
                <div className="flex flex-wrap gap-2 items-center">
                  <MultiSelectFilter
                    title={t("filters.status")}
                    selected={selectedStatuses}
                    onChange={setSelectedStatuses}
                    options={statusOptions}
                  />
                  <MultiSelectFilter
                    title={t("filters.documentTypes")}
                    selected={selectedDocTypes}
                    onChange={setSelectedDocTypes}
                    options={docTypes.map((dt) => ({
                      label: dt.name,
                      value: dt.uuid,
                    }))}
                    disabled={isLoadingDocTypes}
                  />
                  <DateRangeFilter
                    dateFrom={dateFrom}
                    dateTo={dateTo}
                    onDateFromChange={setDateFrom}
                    onDateToChange={setDateTo}
                  />
                  {(selectedStatuses.length > 0 ||
                    selectedDocTypes.length > 0 ||
                    dateFrom ||
                    dateTo) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="p-2"
                      onClick={() => {
                        setSelectedStatuses([]);
                        setSelectedDocTypes([]);
                        handleSearchChange("");
                        setDateFrom("");
                        setDateTo("");
                      }}
                    >
                      <FilterX className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                <SearchInputFilter
                  value={searchTerm}
                  onChange={handleSearchChange}
                  placeholder={t("searchPlaceholder")}
                />
              </div>
            </div>

            <Show when={hasConfirmedDocuments}>
              <div className="bg-green-50 border-b border-green-200 px-8 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-green-800">
                    <Info className="h-4 w-4" />
                    <span>{t("confirmed.message")}</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 bg-white hover:bg-green-50"
                  >
                    {t("confirmed.exportAll")}
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Show>

            <div
              ref={scrollRef}
              className={cn(
                "flex-1 min-h-0 overflow-y-auto overscroll-contain",
                "scrollbar-subtle"
              )}
            >
              <ProcessingJobsTable
                workflowId={wfSlug}
                sets={mergedSets.filter((s) => !deletedSetIds.has(s.setId))}
                liveOverlays={liveOverlays}
                onDelete={(set) => setSetToDelete(set)}
              />
              {isFetchingNextPage && (
                <div className="flex justify-center py-4">
                  <Spinner className="h-5 w-5" />
                </div>
              )}
              {!isFetchingSets && mergedSets.length === 0 && (
                <div className="flex-1 flex items-center justify-center py-12">
                  <EmptyState
                    icon={FileText}
                    title={t("noResultsTitle")}
                    description={t("noResults")}
                  />
                </div>
              )}
            </div>
          </div>
        </Show>
      </PageContent.Body>

      <ConfirmDeleteDialog
        open={setToDelete !== null}
        onOpenChange={(open) => {
          if (!open) setSetToDelete(null);
        }}
        onConfirm={confirmDeleteSet}
        title={t("deleteSetTitle")}
        description={t("deleteSetDescription", { name: deleteSetName })}
        confirmLabel={t("delete")}
        cancelLabel={t("cancel")}
      />
    </PageContent>
  );
}
