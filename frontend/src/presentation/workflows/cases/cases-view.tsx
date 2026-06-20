"use client";

import {
  AlertTriangle,
  Briefcase,
  ChevronRight,
  FileText,
  FilterX,
  MoreVertical,
  Plus,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";

import {
  useCasesInfiniteQuery,
  useCreateCaseMutation,
  useDeleteCaseMutation,
} from "@/src/application/hooks/queries/cases";
import { useDocumentTypesQuery } from "@/src/application/hooks/queries/document-types";
import { queryKeys } from "@/src/application/hooks/queries/keys";
import { useWorkflowQuery } from "@/src/application/hooks/queries/workflows";
import { useDebouncedState } from "@/src/application/hooks/use-debounced-state";
import { useInfiniteScroll } from "@/src/application/hooks/use-infinite-scroll";
import {
  useProcessingJobEvents,
  type SetView,
} from "@/src/application/hooks/use-processing-job-events";
import { caseNoun } from "@/src/application/lib/case-noun";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import type { Case, CaseDocument } from "@/src/domain/entities/case";
import { CaseStatus } from "@/src/domain/entities/case";
import type { DocumentType } from "@/src/domain/entities/doctype";
import { caseNameEditable } from "@/src/domain/entities/workflow";
import {
  isWorkflowProcessingJobInFlight,
  WorkflowProcessingJobStatus,
} from "@/src/domain/events/processing-job-event";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import {
  type FilterOption,
  MultiSelectFilter,
} from "@/src/presentation/components/common/multi-select-filter";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { SearchInputFilter } from "@/src/presentation/components/common/search-input-filter";
import { Show } from "@/src/presentation/components/common/show";
import { DateRangeFilter } from "@/src/presentation/components/filters/date-range-filter";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/src/presentation/components/ui/alert-dialog";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";
import {
  FullPageSpinner,
  Spinner,
} from "@/src/presentation/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/src/presentation/components/ui/tooltip";
import { CreateCaseDialog } from "@/src/presentation/workflows/cases/create-case-dialog";
import { FileUploadButton } from "@/src/presentation/workflows/shared/file-upload-button";
import { ProcessingJobStatusBadge } from "@/src/presentation/workflows/shared/processing-job-status-badge";
import { caseStatusConfig } from "./case-status-config";
import { docStatusConfig } from "./doc-status-config";

const statusConfig = caseStatusConfig;
const TOOLTIP_HOVER_DELAY_MS = 300;
// SSE: refetch una vez en el evento terminal y otra tras este delay, para
// alcanzar el lag de consistencia del backend (espejo de processing-jobs-view).
const SSE_SETTLE_REFETCH_MS = 600;

/**
 * Re-IA 2026-06: los casos `per_upload` nacen con auto-nombre
 * «archivo.ext · ref». La fila muestra el nombre limpio como título y la ref
 * técnica en mono secundaria — nunca el hash como parte del título.
 */
function splitCaseName(name: string): {
  title: string;
  reference: string | null;
} {
  const match = name.match(/^(.*\S)\s+·\s+([0-9a-f]{4,12})$/i);
  if (match) return { title: match[1], reference: match[2] };
  return { title: name, reference: null };
}

export function CasesView() {
  const t = useTranslations("Cases");
  const tNav = useTranslations("Nav");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const queryClient = useQueryClient();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [caseToDelete, setCaseToDelete] = useState<Case | null>(null);

  // E4 · los labels viven en caseStatusConfig (fuente única de los 11
  // estados); el value del filtro viaja tal cual al backend en CSV.
  const caseStatusOptions: FilterOption<CaseStatus>[] = useMemo(
    () =>
      Object.values(CaseStatus).map((status) => ({
        label: caseStatusConfig[status].label,
        value: status,
      })),
    []
  );

  const [selectedStatuses, setSelectedStatuses] = useState<CaseStatus[]>([]);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([]);
  const [withErrors, setWithErrors] = useState(false);
  const [searchTerm, debouncedSearch, handleSearchChange] = useDebouncedState(
    searchParams.get("search") ?? ""
  );
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const activeFilters = useMemo(() => {
    const f: Record<string, string> = {};
    if (debouncedSearch) f.search = debouncedSearch;
    if (selectedStatuses.length > 0) {
      f.statuses = selectedStatuses.join(",");
    }
    if (selectedDocTypes.length > 0)
      f.documentTypes = selectedDocTypes.join(",");
    if (dateFrom) f.dateFrom = dateFrom;
    if (dateTo) f.dateTo = dateTo;
    // Filtro «Con errores»: casos con algún run de procesamiento FAILED.
    if (withErrors) f.withFailedRuns = "true";
    return f;
  }, [
    debouncedSearch,
    selectedStatuses,
    selectedDocTypes,
    dateFrom,
    dateTo,
    withErrors,
  ]);

  const { data: workflow } = useWorkflowQuery(wfSlug);
  const { data: docTypes = [] } = useDocumentTypesQuery(wfSlug);

  // F2/D3: el nombre solo es editable (caso = expediente) en workflows dossier.
  // Gatear sobre un workflow CARGADO: mientras carga, ni "Nuevo caso" ni "Subir"
  // — evita tratar un dossier como per_upload por un estado de carga (F5).
  const workflowLoaded = workflow !== undefined;
  const editable = caseNameEditable(workflow);

  // Sustantivo del caso configurable por workflow (default i18n «Caso/Casos»).
  const noun = caseNoun(workflow, locale, 1);
  const nounPlural = caseNoun(workflow, locale, 2);

  const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage } =
    useCasesInfiniteQuery(wfSlug, activeFilters);

  const allCases = useMemo(
    () => data?.pages.flatMap((p) => p.data) ?? [],
    [data]
  );

  const createCase = useCreateCaseMutation(wfSlug);
  const deleteCase = useDeleteCaseMutation(wfSlug);

  // F6 · SSE en la lista: refetch al cerrar un run (espejo de processing-jobs).
  const refreshCasesList = useCallback(() => {
    void queryClient.refetchQueries({
      queryKey: queryKeys.cases.paginated(wfSlug),
      type: "active",
    });
    void queryClient.refetchQueries({
      queryKey: queryKeys.cases.all(wfSlug),
      type: "active",
    });
  }, [queryClient, wfSlug]);

  const { sets } = useProcessingJobEvents({ workflowId: wfSlug });

  // Progreso del pipeline por caso: el set (run) en vuelo más reciente de cada
  // caso alimenta la barra en la columna Estado (como la vieja tabla de docs).
  const liveSetByCase = useMemo(() => {
    const map = new Map<string, SetView>();
    for (const s of sets) {
      if (!s.workflowCaseId || !isWorkflowProcessingJobInFlight(s.status)) continue;
      // `sets` viene newest-first ⇒ el primero por caso es el run vigente.
      if (!map.has(s.workflowCaseId)) map.set(s.workflowCaseId, s);
    }
    return map;
  }, [sets]);

  const refetchedTerminalSetIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    const terminal = new Set<WorkflowProcessingJobStatus>([
      WorkflowProcessingJobStatus.COMPLETED,
      WorkflowProcessingJobStatus.PARTIAL,
      WorkflowProcessingJobStatus.FAILED,
    ]);
    let triggered = false;
    for (const s of sets) {
      if (terminal.has(s.status) && !refetchedTerminalSetIds.current.has(s.setId)) {
        refetchedTerminalSetIds.current.add(s.setId);
        triggered = true;
      }
    }
    if (!triggered) return;
    refreshCasesList();
    const timer = setTimeout(refreshCasesList, SSE_SETTLE_REFETCH_MS);
    return () => clearTimeout(timer);
  }, [sets, refreshCasesList]);

  const scrollRef = useInfiniteScroll(
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  );

  const isLoading = isFetching && !isFetchingNextPage;

  const hasActiveFilters =
    selectedStatuses.length > 0 ||
    selectedDocTypes.length > 0 ||
    Boolean(dateFrom) ||
    Boolean(dateTo) ||
    withErrors;

  if (isLoading && allCases.length === 0) return <FullPageSpinner />;

  return (
    <PageContent>
      <PageContent.Header
        icon={Briefcase}
        title={workflow?.name || tNav("workflows")}
        subtitle={nounPlural.toUpperCase()}
        showBack
        onBack={() => router.push("/workflows")}
        actions={
          // F4 · CTA capability-adaptive. Dossier ⇒ "Nuevo {caso}"; per_upload ⇒
          // "Subir documentos" (1 archivo → 1 caso auto-nombrado). Mientras el
          // workflow carga ⇒ botón deshabilitado neutro (no asumir per_upload).
          !workflowLoaded ? (
            <Button variant="default" size="sm" disabled>
              <Plus className="h-4 w-4 mr-2" />
              {t("newCase", { noun })}
            </Button>
          ) : editable ? (
            <Button
              variant="default"
              size="sm"
              onClick={() => setShowCreateDialog(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              {t("newCase", { noun })}
            </Button>
          ) : (
            <FileUploadButton
              workflowId={workflow.uuid}
              label={t("uploadDocuments")}
              onDispatched={refreshCasesList}
            />
          )
        }
      />
      <PageContent.Body scroll={false}>
        <div className="flex flex-1 min-h-0 flex-col overflow-hidden rounded-lg border">
          <div className="px-2 py-1 border-b shrink-0">
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-wrap gap-2 items-center">
                <MultiSelectFilter
                  title={t("filters.status")}
                  selected={selectedStatuses}
                  onChange={setSelectedStatuses}
                  options={caseStatusOptions}
                />
                <MultiSelectFilter
                  title={t("filters.documentTypes")}
                  selected={selectedDocTypes}
                  onChange={setSelectedDocTypes}
                  options={docTypes.map((dt) => ({
                    label: dt.name,
                    value: dt.uuid,
                  }))}
                />
                <DateRangeFilter
                  dateFrom={dateFrom}
                  dateTo={dateTo}
                  onDateFromChange={setDateFrom}
                  onDateToChange={setDateTo}
                />
                <Button
                  variant="outline"
                  size="sm"
                  aria-pressed={withErrors}
                  onClick={() => setWithErrors((value) => !value)}
                  className={
                    withErrors
                      ? "bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-100 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800"
                      : ""
                  }
                >
                  <AlertTriangle className="h-3.5 w-3.5 mr-1.5" />
                  {t("filters.withErrors")}
                </Button>
                {hasActiveFilters && (
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
                      setWithErrors(false);
                    }}
                  >
                    <FilterX className="h-4 w-4" />
                  </Button>
                )}
              </div>

              <SearchInputFilter
                value={searchTerm}
                onChange={handleSearchChange}
                placeholder={t("searchPlaceholder", { nounPlural })}
              />
            </div>
          </div>
          <Show
            when={allCases.length > 0 || (isFetching && !isFetchingNextPage)}
            fallback={
              <div className="flex flex-1 items-center justify-center h-full">
                <EmptyState
                  icon={Briefcase}
                  title={t("emptyTitle", { nounPlural })}
                  description={t("emptyDescription", { nounPlural })}
                  // per_upload: crear un caso vacío no tiene sentido (y el
                  // backend lo rechaza, B1a) ⇒ la carga vive en el toolbar.
                  actionLabel={editable ? t("createCase", { noun }) : undefined}
                  onAction={
                    editable ? () => setShowCreateDialog(true) : undefined
                  }
                />
              </div>
            }
          >
            <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/60 hover:bg-muted/60 sticky top-0 z-10">
                    <TableHead className="w-8 pr-0" />
                    <TableHead className="pl-2 text-xs uppercase tracking-wide">
                      {t("columns.name")}
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide">
                      {t("columns.status")}
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide">
                      {t("columns.documents")}
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide">
                      {t("columns.created")}
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide">
                      {t("columns.lastUpdated")}
                    </TableHead>
                    <TableHead className="w-12" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allCases.map((caseItem: Case) => (
                    <CaseRow
                      key={caseItem.uuid}
                      caseItem={caseItem}
                      wfSlug={wfSlug}
                      workflowUuid={workflow?.uuid}
                      editable={editable}
                      docTypes={docTypes}
                      onDelete={() => setCaseToDelete(caseItem)}
                      onUploaded={refreshCasesList}
                      liveSet={liveSetByCase.get(caseItem.uuid)}
                    />
                  ))}
                </TableBody>
              </Table>

              {isFetchingNextPage && (
                <div className="flex justify-center py-4">
                  <Spinner className="h-5 w-5" />
                </div>
              )}

              {!isFetching && allCases.length === 0 && (
                <div className="flex-1 flex items-center justify-center py-12">
                  <EmptyState
                    icon={Briefcase}
                    title={t("emptyTitle", { nounPlural })}
                    description={t("noResults")}
                  />
                </div>
              )}
            </div>
          </Show>
        </div>
      </PageContent.Body>

      <CreateCaseDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSubmit={async (name) => {
          await createCase.mutateAsync(name);
          setShowCreateDialog(false);
        }}
      />

      <AlertDialog
        open={caseToDelete !== null}
        onOpenChange={(open) => {
          if (!open) setCaseToDelete(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle", { noun })}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription", { name: caseToDelete?.name ?? "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (caseToDelete) {
                  deleteCase.mutate(caseToDelete.uuid);
                  setCaseToDelete(null);
                }
              }}
            >
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageContent>
  );
}

function CaseRow({
  caseItem,
  wfSlug,
  workflowUuid,
  editable,
  docTypes,
  onDelete,
  onUploaded,
  liveSet,
}: {
  caseItem: Case;
  wfSlug: string;
  workflowUuid: string | undefined;
  editable: boolean;
  docTypes: DocumentType[];
  onDelete: () => void;
  onUploaded: () => void;
  liveSet: SetView | undefined;
}) {
  const t = useTranslations("Cases");
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const config = statusConfig[caseItem.status];
  const StatusIcon = config.icon;
  const { title, reference } = splitCaseName(caseItem.name);
  // F3/D2: el chevron solo aparece con ≥ 1 doc (no hay empty-state «Sin
  // documentos»; un dossier vacío recién creado no expande).
  const canExpand = caseItem.documents.length >= 1;

  return (
    <>
      <TableRow
        className="cursor-pointer"
        onClick={() => router.push(`/workflows/${wfSlug}/cases/${caseItem.uuid}`)}
      >
        <TableCell className="w-8 pr-0" onClick={(e) => e.stopPropagation()}>
          {canExpand && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              aria-label={t(expanded ? "collapseRowAria" : "expandRowAria", {
                name: caseItem.name,
              })}
              aria-expanded={expanded}
              className="inline-flex items-center justify-center h-7 w-7 rounded-md cursor-pointer text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
              />
            </button>
          )}
        </TableCell>
        <TableCell className="pl-2">
          <div className="flex items-center gap-2">
            <Link
              href={`/workflows/${wfSlug}/cases/${caseItem.uuid}`}
              className="font-medium hover:underline focus-visible:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {title}
            </Link>
            {reference && (
              <span className="font-mono text-xs text-muted-foreground">
                {reference}
              </span>
            )}
          </div>
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-1.5">
            {liveSet ? (
              // Run en vuelo ⇒ barra de progreso del pipeline (paso + %), como
              // la vieja tabla de WorkflowDocuments.
              <ProcessingJobStatusBadge
                status={liveSet.status}
                progressPct={liveSet.progressPct}
                stepLabel={liveSet.currentStep}
                className="min-w-[130px] max-w-[190px]"
              />
            ) : (
              <Badge
                variant={config.variant}
                className={`gap-1.5 ${config.className}`}
              >
                <StatusIcon className="h-3 w-3" />
                {config.label}
              </Badge>
            )}
            {caseItem.hasFailedRuns && (
              <Tooltip delay={TOOLTIP_HOVER_DELAY_MS}>
                <TooltipTrigger
                  render={(triggerProps) => (
                    <Badge
                      {...triggerProps}
                      variant="outline"
                      className="gap-1 bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800"
                    >
                      <AlertTriangle className="h-3 w-3" />
                      {t("failedRuns")}
                    </Badge>
                  )}
                />
                <TooltipContent>{t("failedRunsTooltip")}</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            {caseItem.documentsCount}
          </div>
        </TableCell>
        <TableCell>
          <span className="text-sm text-muted-foreground">
            {formatRelativeDate(caseItem.createdAt)}
          </span>
        </TableCell>
        <TableCell>
          <span className="text-sm text-muted-foreground">
            {formatRelativeDate(caseItem.updatedAt)}
          </span>
        </TableCell>
        <TableCell onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-end gap-1.5">
            {/* F4 · case-centric: "Añadir documentos" por fila, atado a este caso
                (D5: en dossier la carga siempre lleva workflowCaseId). */}
            {editable && workflowUuid && (
              <FileUploadButton
                workflowId={workflowUuid}
                workflowCaseId={caseItem.uuid}
                label={t("addDocuments")}
                compact
                onDispatched={onUploaded}
              />
            )}
            <DropdownMenu>
              <DropdownMenuTrigger
                onClick={(e) => e.stopPropagation()}
                aria-label={t("rowMenuAria", { name: caseItem.name })}
                className="inline-flex items-center justify-center h-8 w-8 rounded-md cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <MoreVertical className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  variant="destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete();
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </TableCell>
      </TableRow>
      {expanded &&
        caseItem.documents.map((doc) => (
          <CaseDocumentSubRow
            key={doc.uuid}
            doc={doc}
            wfSlug={wfSlug}
            docTypes={docTypes}
          />
        ))}
    </>
  );
}

function CaseDocumentSubRow({
  doc,
  wfSlug,
  docTypes,
}: {
  doc: CaseDocument;
  wfSlug: string;
  docTypes: DocumentType[];
}) {
  const t = useTranslations("Cases");
  const router = useRouter();
  // Click en el workflow_document ⇒ abre su detalle (misma ruta que la tabla
  // de processing-jobs: /workflows/{wf}/documents/{docId}).
  const href = `/workflows/${wfSlug}/documents/${doc.uuid}`;
  const docConfig = docStatusConfig[doc.status];
  const DocIcon = docConfig.icon;
  // El per-doc de la lista trae documentTypeId, no el objeto: lookup contra los
  // doctypes ya cargados del workflow.
  const typeName = doc.documentTypeId
    ? (docTypes.find((dt) => dt.uuid === doc.documentTypeId)?.name ?? null)
    : null;
  // Una sola página ⇒ solo el número (`P.1`); rango solo si abarca >1 página.
  const pageLabel = doc.pageRange
    ? doc.pageRange.from === doc.pageRange.to
      ? `${doc.pageRange.from}`
      : `${doc.pageRange.from}–${doc.pageRange.to}`
    : null;

  return (
    <TableRow
      className="cursor-pointer bg-muted/30 hover:bg-muted/50"
      onClick={() => router.push(href)}
    >
      <TableCell />
      <TableCell className="pl-2">
        <div className="flex items-center gap-2 pl-2">
          <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <Link
            href={href}
            className="text-sm hover:underline focus-visible:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {doc.fileName ?? t("untitledDocument")}
          </Link>
          {typeName && (
            <span className="text-xs text-muted-foreground">· {typeName}</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={docConfig.variant} className="gap-1.5">
          <DocIcon className="h-3 w-3" />
          {docConfig.label}
        </Badge>
      </TableCell>
      <TableCell>
        {pageLabel && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {t("pagesLabel", { range: pageLabel })}
          </span>
        )}
      </TableCell>
      <TableCell colSpan={3} />
    </TableRow>
  );
}
