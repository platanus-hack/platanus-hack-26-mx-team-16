"use client";

import {
  Expand,
  FileText,
  History,
  Pencil,
  PlayCircle,
  ShieldCheck,
  Shrink,
  Sparkles,
  Square,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAnalysisRuns } from "@/src/application/hooks/use-analysis-runs";
import { usePersistedPaneSize } from "@/src/application/hooks/use-persisted-pane-size";
import { useProcessingJobEvents } from "@/src/application/hooks/use-processing-job-events";
import { useWorkflowQuery } from "@/src/application/hooks/queries/workflows";
import { useWorkflowCaseDetailStore } from "@/src/application/stores/workflow-case-detail-store";
import { CaseStatus } from "@/src/domain/entities/case";
import { caseNameEditable } from "@/src/domain/entities/workflow";
import { isWorkflowProcessingJobInFlight } from "@/src/domain/events/processing-job-event";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowProcessingJobRepository } from "@/src/infrastructure/repositories/http-workflow-processing-job";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import {
  PageContent,
  PaneSize,
} from "@/src/presentation/components/common/page-content";
import { TabsWithActions } from "@/src/presentation/components/common/tabs-with-actions";
import { Badge } from "@/src/presentation/components/ui/badge";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
import { CaseBlockersPanel } from "@/src/presentation/workflows/cases/case-blockers-panel";
import { CaseChildrenPanel } from "@/src/presentation/workflows/cases/case-children-panel";
import { CaseCommentComposer } from "@/src/presentation/workflows/cases/case-comment-composer";
import { CaseCompletenessBar } from "@/src/presentation/workflows/cases/case-completeness-bar";
import { caseStatusConfig } from "@/src/presentation/workflows/cases/case-status-config";
import { CaseTimeline } from "@/src/presentation/workflows/cases/case-timeline";
import { MarkReadyButton } from "@/src/presentation/workflows/cases/mark-ready-button";
import { FileUploadButton } from "@/src/presentation/workflows/shared/file-upload-button";
import { LiveAnalysisRunsPane } from "./bottom-panes/analysis-runs";
import { isExpandableResult } from "./cards/analysis-rule-results";
import { WorkflowAnalysisTab } from "./tabs/analysis";
import { WorkflowCaseDocumentsTab } from "./tabs/documents";

const processingJobRepository = new HttpWorkflowProcessingJobRepository(
  authHttp
);

const CASE_DETAIL_TABS = ["documents", "analysis", "timeline"] as const;
type CaseDetailTab = (typeof CASE_DETAIL_TABS)[number];
const DEFAULT_TAB: CaseDetailTab = "documents";

interface Props {
  workflowUuid: string;
  caseId: string;
}

export function WorkflowCaseDetailView({ workflowUuid, caseId }: Props) {
  const t = useTranslations("CaseDetail");
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab: CaseDetailTab = (
    CASE_DETAIL_TABS as readonly string[]
  ).includes(tabParam ?? "")
    ? (tabParam as CaseDetailTab)
    : DEFAULT_TAB;
  const [activeTab, setActiveTab] = useState<CaseDetailTab>(initialTab);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value as CaseDetailTab);
      router.replace(
        `/workflows/${workflowUuid}/cases/${caseId}?tab=${value}`,
        { scroll: false }
      );
    },
    [router, workflowUuid, caseId]
  );
  const { caseDetail, isLoading, loadCase, updateName, observeSets } =
    useWorkflowCaseDetailStore();
  const { data: workflow } = useWorkflowQuery(workflowUuid);
  // F5/D3: el nombre solo es editable en workflows dossier (multi_doc_dossier);
  // en per_upload lo fija el archivo y el backend rechaza el rename (B1b).
  const nameEditable = caseNameEditable(workflow);
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const nameInputRef = useRef<HTMLInputElement>(null);

  const refreshCase = useCallback(
    () => loadCase(workflowUuid, caseId),
    [loadCase, workflowUuid, caseId]
  );

  // Single source of truth for the live processing feed. The hook opens
  // the SSE stream against the unified processing_job endpoint and reduces
  // incoming events into a per-set view model.
  const { sets, documents } = useProcessingJobEvents({
    workflowId: workflowUuid,
    workflowCaseId: caseId,
  });

  const analysisRuns = useAnalysisRuns(workflowUuid, caseId);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [forceCancelDialogOpen, setForceCancelDialogOpen] = useState(false);

  const [analysisPaneSize, setAnalysisPaneSize] = usePersistedPaneSize(
    "doxiq:case-detail:analysis-pane-size",
    PaneSize.Min
  );
  const [isReExtracting, setIsReExtracting] = useState(false);
  // Re-IA 2026-06: «Reintentar» de runs FAILED desde la Actividad.
  const [retryingJobIds, setRetryingJobIds] = useState<Set<string>>(
    () => new Set()
  );

  const handleRetryJob = useCallback(
    async (processingJobId: string) => {
      setRetryingJobIds((prev) => new Set(prev).add(processingJobId));
      const res = await processingJobRepository.retry({
        workflowId: workflowUuid,
        processingJobId,
      });
      setRetryingJobIds((prev) => {
        const next = new Set(prev);
        next.delete(processingJobId);
        return next;
      });
      if (!("data" in res)) {
        console.error("retry failed", res);
      }
      // El SSE actualiza `sets` solo; el dot LIVE de Actividad toma el relevo.
    },
    [workflowUuid]
  );

  const inFlightSetIds = useMemo(
    () =>
      new Set(
        sets
          .filter((s) => isWorkflowProcessingJobInFlight(s.status))
          .map((s) => s.setId)
      ),
    [sets]
  );

  // WorkflowDocument ids whose parent set is currently in PROCESSING/PENDING.
  // We can't go through `set.fileId` because that's only set by the
  // `dispatched` event, which the SSE replay window doesn't emit for
  // historical sets. The hook's per-doc map (`document_persisted` events)
  // gives us the `(processingJobId → documentId)` join we need.
  const reExtractingDocumentIds = useMemo(
    () =>
      new Set(
        documents
          .filter((d) => inFlightSetIds.has(d.processingJobId))
          .map((d) => d.documentId)
      ),
    [documents, inFlightSetIds]
  );

  // E4 · doc_type slug → nombre legible para la barra de completitud y la
  // lista de faltantes del dialog de «Marcar listo».
  const docTypeNames = useMemo(() => {
    const names: Record<string, string> = {};
    for (const group of caseDetail?.documentGroups ?? []) {
      if (group.documentType.slug) {
        names[group.documentType.slug] = group.documentType.name;
      }
    }
    return names;
  }, [caseDetail?.documentGroups]);

  const expandableIds = useMemo(
    () => analysisRuns.results.filter(isExpandableResult).map((r) => r.uuid),
    [analysisRuns.results]
  );
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const allExpanded =
    expandableIds.length > 0 && expandedIds.size === expandableIds.length;
  const toggleRow = useCallback(
    (uuid: string) =>
      setExpandedIds((prev) => {
        const next = new Set(prev);
        if (next.has(uuid)) next.delete(uuid);
        else next.add(uuid);
        return next;
      }),
    []
  );
  const toggleAllResults = useCallback(
    () => setExpandedIds(allExpanded ? new Set() : new Set(expandableIds)),
    [allExpanded, expandableIds]
  );

  useEffect(() => {
    if (caseDetail) setNameValue(caseDetail.name || "");
  }, [caseDetail]);

  const handleNameBlur = useCallback(async () => {
    setEditingName(false);
    const trimmed = (nameValue || "").trim();
    if (!trimmed || trimmed === caseDetail?.name) {
      setNameValue(caseDetail?.name || "");
      return;
    }
    await updateName(workflowUuid, caseId, trimmed);
  }, [caseDetail?.name, caseId, nameValue, workflowUuid, updateName]);

  const startEditingName = useCallback(() => {
    setEditingName(true);
    requestAnimationFrame(() => {
      nameInputRef.current?.focus();
      nameInputRef.current?.select();
    });
  }, []);

  useEffect(() => {
    void refreshCase();
    return () => {
      useWorkflowCaseDetailStore.getState().reset();
    };
  }, [refreshCase]);

  // The store diffs SSE set statuses across renders and refetches the
  // case detail whenever any set transitions from in-flight → terminal,
  // so the per-document data behind `documentGroups` lands in PG before
  // the cards refresh.
  useEffect(() => {
    observeSets(workflowUuid, caseId, sets);
  }, [observeSets, workflowUuid, caseId, sets]);

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!caseDetail) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">{t("notFound")}</div>
      </div>
    );
  }

  const statusCfg = caseStatusConfig[caseDetail.status];
  const StatusIcon = statusCfg.icon;

  const titleNode = !nameEditable ? (
    // per_upload: nombre derivado del archivo, no editable (sin pencil/click).
    <span className="px-1 text-xl font-semibold leading-tight">
      {caseDetail.name || t("untitled")}
    </span>
  ) : editingName ? (
    <input
      ref={nameInputRef}
      type="text"
      value={nameValue ?? ""}
      onChange={(e) => setNameValue(e.target.value)}
      onBlur={handleNameBlur}
      onKeyDown={(e) => {
        if (e.key === "Enter") nameInputRef.current?.blur();
        if (e.key === "Escape") {
          setNameValue(caseDetail.name);
          setEditingName(false);
        }
      }}
      placeholder={t("untitled")}
      className="min-w-[240px] max-w-md border-b-2 border-primary bg-transparent px-1 py-0.5 text-xl font-semibold leading-tight outline-none"
      autoFocus
    />
  ) : (
    <button
      type="button"
      onClick={startEditingName}
      aria-label={t("editNameAria")}
      className="group -mx-1 flex cursor-text items-center gap-2 rounded-md px-1 text-left text-xl font-semibold leading-tight transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      {caseDetail.name || t("untitled")}
      <Pencil className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
    </button>
  );

  const subtitleNode = (
    <p
      className={`flex flex-wrap items-center gap-x-2 font-mono text-xs tracking-wide text-muted-foreground transition-opacity ${
        editingName ? "opacity-40" : "opacity-100"
      }`}
    >
      {caseId}
      {/* E5 · lineage del fan-out: el child enlaza a su caso padre. */}
      {caseDetail.parentCaseId && (
        <Link
          href={`/workflows/${workflowUuid}/cases/${caseDetail.parentCaseId}`}
          className="font-sans text-primary underline-offset-2 hover:underline"
        >
          ↳ parte del caso {caseDetail.parentCaseId.slice(0, 8)}
        </Link>
      )}
    </p>
  );

  const hasDocuments = caseDetail.documentGroups.some(
    (group) => group.documents.length > 0
  );

  const hasAnyProcessingJob = sets.length > 0;
  const anyDocSetInFlight = inFlightSetIds.size > 0;
  const reExtractDisabled =
    !hasAnyProcessingJob ||
    anyDocSetInFlight ||
    analysisRuns.isLive ||
    analysisRuns.isStarting ||
    isReExtracting;

  const reExtractTitle = !hasAnyProcessingJob
    ? t("needDocumentToReextract")
    : anyDocSetInFlight
      ? t("waitProcessing")
      : analysisRuns.isLive || analysisRuns.isStarting
        ? t("cancelAnalysisFirst")
        : undefined;

  const handleReExtractFields = async () => {
    if (reExtractDisabled) return;
    setIsReExtracting(true);
    handleTabChange("documents");
    const res = await processingJobRepository.reExtractCaseFields({
      workflowId: workflowUuid,
      caseId,
    });
    // Backend dispatches a Temporal workflow per set; the SSE will start
    // emitting `step_started` events shortly. Reset the local guard once
    // the dispatch acknowledgment lands; the in-flight check above will
    // take over via the SSE-driven `sets` array.
    setIsReExtracting(false);
    if (!("data" in res)) {
      console.error("re-extract failed", res);
    }
  };

  const uploadAction = {
    label: t("uploadDocument"),
    render: () => (
      <FileUploadButton
        workflowId={workflowUuid}
        workflowCaseId={caseId}
        onDispatched={() => {
          handleTabChange("documents");
          void refreshCase();
        }}
      />
    ),
  };

  const reExtractAction = {
    label: t("extractFields"),
    icon: Sparkles,
    onClick: () => {
      void handleReExtractFields();
    },
    disabled: reExtractDisabled,
    title: reExtractTitle,
  };

  const analysisAction = analysisRuns.isLive
    ? {
        label: analysisRuns.isCanceling
          ? t("forceCancel")
          : t("cancelAnalysis"),
        icon: Square,
        onClick: () => {
          if (analysisRuns.isCanceling) {
            setForceCancelDialogOpen(true);
          } else {
            setCancelDialogOpen(true);
          }
        },
        variant: "destructive" as const,
      }
    : {
        label: t("runAnalysis"),
        icon: PlayCircle,
        onClick: () => {
          if (analysisRuns.isStarting || !hasDocuments) return;
          handleTabChange("analysis");
          setAnalysisPaneSize(PaneSize.Expanded);
          void analysisRuns.startRun();
        },
        variant: "primary" as const,
        disabled: !hasDocuments,
        title: hasDocuments ? undefined : t("needDocumentToAnalyze"),
      };

  // Re-extract is per-case but only conceptually relevant from the
  // Documents tab — the user picks which sets to refresh from there.
  const documentsActions = [uploadAction, reExtractAction, analysisAction];

  const analysisActions =
    expandableIds.length > 0
      ? [
          {
            label: allExpanded ? t("collapse") : t("expand"),
            icon: allExpanded ? Shrink : Expand,
            onClick: toggleAllResults,
          },
          uploadAction,
          analysisAction,
        ]
      : [uploadAction, analysisAction];

  return (
    <>
      <PageContent>
        <PageContent.Header
          icon={FileText}
          title={titleNode}
          subtitle={subtitleNode}
          showBack
          onBack={() => router.push(`/workflows/${workflowUuid}/cases`)}
          actions={
            <div className="flex items-center gap-2">
              {caseDetail.status === CaseStatus.RECEIVING && (
                <MarkReadyButton
                  workflowUuid={workflowUuid}
                  caseId={caseId}
                  docTypeNames={docTypeNames}
                  onReady={() => void refreshCase()}
                />
              )}
              <Badge
                variant={statusCfg.variant}
                className={`gap-1.5 px-3.5 text-sm h-9 [&>svg]:!size-4 ${statusCfg.className}`}
              >
                <StatusIcon />
                {statusCfg.label}
              </Badge>
            </div>
          }
        />

        <PageContent.Body scroll={false}>
          {caseDetail.completeness && (
            <CaseCompletenessBar
              completeness={caseDetail.completeness}
              readyAt={caseDetail.readyAt}
              docTypeNames={docTypeNames}
            />
          )}
          {/* E5 · «este caso está aquí porque…» (gate items + reglas BLOCKER
            de la APPROVAL abierta) + lock visible. Se oculta solo. */}
          <CaseBlockersPanel caseId={caseId} results={analysisRuns.results} />
          {/* E5 · fan-out: resumen + lista de children en el padre. */}
          {caseDetail.children && caseDetail.children.total > 0 && (
            <CaseChildrenPanel
              workflowUuid={workflowUuid}
              caseId={caseId}
              summary={caseDetail.children}
            />
          )}
          <TabsWithActions
            value={activeTab}
            onValueChange={handleTabChange}
            contentClassName="overflow-y-auto pb-14"
            tabs={[
              {
                value: "documents",
                label: t("tabs.documents"),
                icon: FileText,
                content: (
                  <WorkflowCaseDocumentsTab
                    workflowUuid={workflowUuid}
                    caseId={caseId}
                    documentGroups={caseDetail.documentGroups}
                    reExtractingDocumentIds={reExtractingDocumentIds}
                    onDocumentsChanged={refreshCase}
                  />
                ),
                actions: documentsActions,
              },
              {
                value: "analysis",
                label: t("tabs.analysis"),
                icon: ShieldCheck,
                content: (
                  <WorkflowAnalysisTab
                    runs={analysisRuns}
                    paneOpen={analysisPaneSize !== PaneSize.Min}
                    expandedIds={expandedIds}
                    onToggleRow={toggleRow}
                  />
                ),
                actions: analysisActions,
              },
              {
                value: "timeline",
                label: (
                  <span className="flex items-center gap-1.5">
                    {t("tabs.timeline")}
                    {anyDocSetInFlight && (
                      <span
                        aria-hidden
                        className="size-1.5 rounded-full bg-primary animate-pulse motion-reduce:animate-none"
                      />
                    )}
                  </span>
                ),
                icon: History,
                content: (
                  <div className="space-y-5">
                    {/* E5 · composer → case_event comment.added */}
                    <CaseCommentComposer
                      workflowUuid={workflowUuid}
                      caseId={caseId}
                      onPosted={() => void refreshCase()}
                    />
                    {/* Re-IA 2026-06: runs técnicos intercalados (el drawer
                      «Documentos Procesados» se absorbió aquí). */}
                    <CaseTimeline
                      events={caseDetail.timeline ?? []}
                      jobs={sets}
                      onRetryJob={(id) => void handleRetryJob(id)}
                      retryingJobIds={retryingJobIds}
                    />
                  </div>
                ),
              },
            ]}
          />
        </PageContent.Body>

        {activeTab === "analysis" ? (
          <PageContent.LiveBottomPane
            size={analysisPaneSize}
            onSizeChange={setAnalysisPaneSize}
          >
            <LiveAnalysisRunsPane
              history={analysisRuns.history}
              activeRun={analysisRuns.activeRun}
              isLive={analysisRuns.isLive}
              isHydrated={analysisRuns.isHydrated}
              completed={analysisRuns.completedEvaluations}
              total={analysisRuns.totalEvaluations}
              onSelect={analysisRuns.selectRun}
            />
          </PageContent.LiveBottomPane>
        ) : null}
      </PageContent>
      <ConfirmDeleteDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        onConfirm={() => {
          setCancelDialogOpen(false);
          void analysisRuns.cancelRun();
        }}
        title={t("cancelDialog.title")}
        description={t("cancelDialog.description")}
        confirmLabel={t("cancelDialog.confirm")}
        cancelLabel={t("cancelDialog.cancel")}
      />
      <ConfirmDeleteDialog
        open={forceCancelDialogOpen}
        onOpenChange={setForceCancelDialogOpen}
        onConfirm={() => {
          setForceCancelDialogOpen(false);
          void analysisRuns.forceCancelRun();
        }}
        title={t("forceCancelDialog.title")}
        description={t("forceCancelDialog.description")}
        confirmLabel={t("forceCancelDialog.confirm")}
        cancelLabel={t("forceCancelDialog.cancel")}
      />
    </>
  );
}
