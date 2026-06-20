"use client";

import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Info,
  MinusCircle,
  ShieldCheck,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useCallback, useMemo, useState } from "react";
import { useDocumentTypesQuery } from "@/src/application/hooks/queries/document-types";
import {
  CaseLockedError,
  useVerifyFieldsMutation,
} from "@/src/application/hooks/queries/workflow-documents";
import { shortUuid } from "@/src/application/lib/short-uuid";
import { cn } from "@/src/application/lib/utils";
import { authHttp } from "@/src/infrastructure/http/client";
import type {
  MappedField,
  WorkflowDocumentDetail,
} from "@/src/infrastructure/repositories/http-workflow-document";
import { Badge } from "@/src/presentation/components/ui/badge";
import { JsonViewer } from "@/src/presentation/components/ui/json-viewer";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import {
  type ExtractionView,
  ExtractionViewToggle,
} from "./extraction-view-toggle";
import { renderExtractedValue } from "./mapped-extraction-field";
import { MappedExtractionList } from "./mapped-extraction-list";

interface DocumentDataPaneProps {
  document: WorkflowDocumentDetail;
  /** Currently highlighted field key (mirrors `activeBoxId` minus the
   *  `field:` prefix). */
  activeFieldKey?: string | null;
  /** Fired when the user clicks a row — parent uses it to drive
   *  `PDFViewer.activeBoxId` so the viewer scrolls to the bbox. */
  onFieldSelect?: (fieldKey: string) => void;
  /**
   * E5 · bench editable (aceptar/corregir por campo). Se auto-desactiva si
   * falta el contexto workflow+caso (p. ej. consola staff read-only).
   */
  editable?: boolean;
}

interface ValidationItem {
  rule_id?: string;
  field?: string;
  status?: string;
  severity?: string;
  reason?: string;
  value_analyzed?: string;
  [key: string]: unknown;
}

const MIME_TO_EXT: Record<string, string> = {
  "application/pdf": "pdf",
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/jpg": "jpg",
  "image/webp": "webp",
  "image/heic": "heic",
  "application/msword": "doc",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "docx",
  "application/vnd.ms-excel": "xls",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
  "text/csv": "csv",
  "text/plain": "txt",
};

function fileNameWithExtension(
  name: string | null,
  mime: string | null
): string | null {
  if (!name) return null;
  if (/\.[a-z0-9]+$/i.test(name)) return name;
  const ext = mime ? MIME_TO_EXT[mime] : null;
  return ext ? `${name}.${ext}` : name;
}

type SeverityVariant = "success" | "warning" | "destructive" | "secondary";
type SeverityLabelKey = "passed" | "failed" | "needsReview";

// Maps a raw validation status to the shared Badge state vocabulary, so a rule
// outcome looks the same here as everywhere else. The amber needs-review band is
// the one a reviewer must not miss; it can never collapse into the neutral fallback.
// Returns a translation key for known states; `fallback` carries an unrecognized
// raw status through verbatim so the reviewer still sees what the backend sent.
function severityBadge(status?: string): {
  labelKey: SeverityLabelKey | null;
  fallback: string | null;
  variant: SeverityVariant;
  Icon: typeof CheckCircle2;
} {
  switch ((status ?? "").toLowerCase()) {
    case "passed":
    case "pass":
    case "ok":
      return {
        labelKey: "passed",
        fallback: null,
        variant: "success",
        Icon: CheckCircle2,
      };
    case "failed":
    case "fail":
    case "error":
      return {
        labelKey: "failed",
        fallback: null,
        variant: "destructive",
        Icon: AlertCircle,
      };
    case "warning":
    case "warn":
    case "needs_review":
    case "needs-review":
    case "review":
    case "low_confidence":
    case "soft_fail":
      return {
        labelKey: "needsReview",
        fallback: null,
        variant: "warning",
        Icon: AlertTriangle,
      };
    default:
      return {
        labelKey: null,
        fallback: status || null,
        variant: "secondary",
        Icon: MinusCircle,
      };
  }
}

export function DocumentDataPane({
  document,
  activeFieldKey,
  onFieldSelect,
  editable = true,
}: DocumentDataPaneProps) {
  const t = useTranslations("DocumentDataPane");
  const params = useParams();
  const wfSlug = params.wfSlug as string | undefined;
  const { data: docTypes } = useDocumentTypesQuery(wfSlug ?? "");
  const docTypeName = useMemo(() => {
    if (!document.documentTypeId) return null;
    return (
      docTypes?.find((t) => t.uuid === document.documentTypeId)?.name ?? null
    );
  }, [docTypes, document.documentTypeId]);
  const fileUrl = document.fileId
    ? `/api/v1/documents/${document.fileId}/download`
    : null;

  const openFileInNewTab = useCallback(
    async (e: React.MouseEvent<HTMLAnchorElement>) => {
      if (!document.fileId) return;
      e.preventDefault();
      const res = await authHttp.get<{
        data: { presigned_url?: string | null };
      }>(`/v1/documents/${document.fileId}`);
      const url = res.data.data.presigned_url;
      if (!url) return;
      window.open(url, "_blank", "noopener,noreferrer");
    },
    [document.fileId]
  );

  const [activeTab, setActiveTab] = useState("data");
  const [extractionView, setExtractionView] =
    useState<ExtractionView>("fields");

  // E5 · confianza por campo: `fieldConfidence` del backend con fallback al
  // mínimo de las bboxes del campo (un campo dudoso debe VERSE dudoso).
  const fieldConfidenceMap = useMemo(() => {
    const map: Record<string, number | null> = {};
    for (const [key, raw] of Object.entries(document.mappedExtraction ?? {})) {
      const direct = document.fieldConfidence?.[key];
      if (typeof direct === "number") {
        map[key] = direct;
        continue;
      }
      const bboxConfidences = ((raw as MappedField)?.bbox ?? [])
        .map((b) => b.confidence)
        .filter((c): c is number => typeof c === "number");
      map[key] = bboxConfidences.length ? Math.min(...bboxConfidences) : null;
    }
    return map;
  }, [document.mappedExtraction, document.fieldConfidence]);

  // Prefer `mapped_extraction` (richer: per-field bbox + page) over the
  // flat `extraction` dict. Fall back to extraction when the worker
  // hasn't produced a mapped output yet.
  // E5 · orden por confianza ASCENDENTE: lo más dudoso primero (Inspection
  // Bench); los campos sin confianza conocida van al final.
  const mappedEntries = useMemo(
    () =>
      Object.entries(document.mappedExtraction ?? {}).sort((a, b) => {
        const ca = fieldConfidenceMap[a[0]] ?? 2;
        const cb = fieldConfidenceMap[b[0]] ?? 2;
        return ca - cb;
      }),
    [document.mappedExtraction, fieldConfidenceMap]
  );
  const fallbackExtractionEntries = useMemo(
    () =>
      mappedEntries.length === 0
        ? Object.entries(document.extraction ?? {})
        : [],
    [mappedEntries.length, document.extraction]
  );
  const totalEntries = mappedEntries.length || fallbackExtractionEntries.length;
  const validation = useMemo(
    () => (document.validation ?? []) as ValidationItem[],
    [document.validation]
  );

  // E5 · bench editable: la mutación exige el binding workflow→caso→doc.
  const canEdit = editable && Boolean(wfSlug) && Boolean(document.caseId);
  const verifyFields = useVerifyFieldsMutation(
    wfSlug ?? "",
    document.caseId ?? "",
    document.uuid
  );
  const [busyFieldKey, setBusyFieldKey] = useState<string | null>(null);
  const [benchError, setBenchError] = useState<string | null>(null);
  const flaggedFields = useMemo(
    () => new Set(document.needsClarification ?? []),
    [document.needsClarification]
  );

  const runVerify = useCallback(
    (fieldKey: string, action: "accept" | "correct", value?: unknown) => {
      if (!canEdit || verifyFields.isPending) return;
      setBenchError(null);
      setBusyFieldKey(fieldKey);
      verifyFields.mutate(
        action === "correct"
          ? [{ fieldPath: fieldKey, action, value }]
          : [{ fieldPath: fieldKey, action }],
        {
          onError: (error) => {
            setBenchError(
              error instanceof CaseLockedError
                ? t("bench.locked", { holder: error.holder ?? "—" })
                : error.message
            );
          },
          onSettled: () => setBusyFieldKey(null),
        }
      );
    },
    [canEdit, verifyFields, t]
  );

  const handleAccept = useCallback(
    (fieldKey: string) => runVerify(fieldKey, "accept"),
    [runVerify]
  );
  const handleCorrect = useCallback(
    (fieldKey: string, value: unknown) => runVerify(fieldKey, "correct", value),
    [runVerify]
  );

  return (
    <div className="bg-card flex flex-col w-full h-full">
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="w-full flex flex-col flex-1 min-h-0"
      >
        <div className="border-b flex-none">
          <TabsList
            variant="line"
            className="w-full justify-start bg-transparent"
          >
            <TabsTrigger variant="line" value="data" className="gap-2">
              <FileText className="h-4 w-4" />
              <span className="text-sm">{t("tabs.extraction")}</span>
              {totalEntries > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {totalEntries}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger variant="line" value="validation" className="gap-2">
              <ShieldCheck className="h-4 w-4" />
              <span className="text-sm">{t("tabs.validation")}</span>
              {validation.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {validation.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger variant="line" value="metadata" className="gap-2">
              <Info className="h-4 w-4" />
              <span className="text-sm">{t("tabs.metadata")}</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          {/* Extracción */}
          <TabsContent
            value="data"
            className={cn(
              "mt-0",
              totalEntries === 0
                ? "h-full p-6 flex items-center justify-center"
                : "p-6 space-y-4"
            )}
          >
            {totalEntries === 0 ? (
              <EmptyState
                title={t("emptyTitle")}
                description={t("emptyDescription")}
              />
            ) : (
              <>
                <div className="flex justify-end">
                  <ExtractionViewToggle
                    value={extractionView}
                    onChange={setExtractionView}
                  />
                </div>

                {benchError && (
                  <p
                    role="alert"
                    className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  >
                    {benchError}
                  </p>
                )}

                {extractionView === "json" ? (
                  <JsonViewer
                    value={document.extraction ?? {}}
                    downloadFileName={`${(document.fileName ?? "document").replace(/\.[^./\\]+$/, "")}_${shortUuid(document.uuid)}.json`}
                  />
                ) : extractionView === "plain" ? (
                  <PlainTextView
                    text={document.extractedText}
                    emptyLabel={t("plainEmpty")}
                  />
                ) : mappedEntries.length > 0 ? (
                  <MappedExtractionList
                    entries={mappedEntries}
                    activeFieldKey={activeFieldKey}
                    onFieldSelect={onFieldSelect}
                    fieldConfidence={fieldConfidenceMap}
                    verification={document.verification ?? null}
                    flaggedFields={flaggedFields}
                    editable={canEdit}
                    busyFieldKey={busyFieldKey}
                    onAccept={handleAccept}
                    onCorrect={handleCorrect}
                  />
                ) : (
                  <div className="space-y-3">
                    {fallbackExtractionEntries.map(([key, value]) => (
                      <div
                        key={key}
                        className="grid grid-cols-2 gap-4 py-2 border-b last:border-b-0"
                      >
                        <div className="text-sm text-muted-foreground font-mono break-all">
                          {key}
                        </div>
                        <div className="text-sm font-medium break-all">
                          {renderExtractedValue(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* Validación */}
          <TabsContent
            value="validation"
            className={cn(
              "mt-0",
              validation.length === 0
                ? "h-full p-6 flex items-center justify-center"
                : "p-6 space-y-3"
            )}
          >
            {validation.length === 0 ? (
              <EmptyState
                title={t("validationEmptyTitle")}
                description={t("validationEmptyDescription")}
              />
            ) : (
              validation.map((item, idx) => {
                const badge = severityBadge(item.status);
                const BadgeIcon = badge.Icon;
                const badgeLabel = badge.labelKey
                  ? t(`status.${badge.labelKey}`)
                  : (badge.fallback ?? t("status.unknown"));
                return (
                  <div
                    key={item.rule_id ?? idx}
                    className="rounded-lg border p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={badge.variant} className="gap-1.5">
                          <BadgeIcon className="h-3 w-3" />
                          {badgeLabel}
                        </Badge>
                        {item.field && (
                          <span className="text-xs font-mono text-muted-foreground">
                            {item.field}
                          </span>
                        )}
                      </div>
                      {item.rule_id && (
                        <span className="text-xs text-muted-foreground font-mono">
                          {item.rule_id}
                        </span>
                      )}
                    </div>
                    {item.reason && (
                      <p className="text-sm text-foreground/80">
                        {item.reason}
                      </p>
                    )}
                    {item.value_analyzed !== undefined && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">
                          {t("valueAnalyzed")}:{" "}
                        </span>
                        <span className="font-mono">
                          {renderExtractedValue(item.value_analyzed)}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </TabsContent>

          {/* Metadata */}
          <TabsContent value="metadata" className="mt-0 p-6 space-y-4">
            <MetaRow label={t("meta.documentId")} value={document.uuid} mono />
            <MetaRow
              label={t("meta.fileId")}
              value={document.fileId ?? "—"}
              mono
            />
            <MetaRow
              label={t("meta.fileName")}
              value={(() => {
                const displayName = fileNameWithExtension(
                  document.fileName,
                  document.mimeType
                );
                if (!displayName) return "—";
                if (!fileUrl) {
                  return (
                    <span className="font-semibold break-all">
                      {displayName}
                    </span>
                  );
                }
                return (
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={openFileInNewTab}
                    className="font-semibold break-all text-primary underline-offset-2 hover:underline"
                  >
                    {displayName}
                  </a>
                );
              })()}
            />
            <MetaRow
              label={t("meta.documentType")}
              value={
                document.documentTypeId ? (
                  <span className="font-mono break-all">
                    {document.documentTypeId}
                    {docTypeName ? (
                      <span className="font-sans text-muted-foreground">
                        <span className="mx-1">/</span>
                        {docTypeName}
                      </span>
                    ) : null}
                  </span>
                ) : (
                  "—"
                )
              }
            />
            <MetaRow
              label={t("meta.status")}
              value={<Badge variant="secondary">{document.status}</Badge>}
            />
            <MetaRow
              label={t("meta.source")}
              value={<Badge variant="secondary">{document.source}</Badge>}
            />
            <MetaRow
              label={t("meta.created")}
              value={
                document.createdAt
                  ? new Date(document.createdAt).toLocaleString()
                  : "—"
              }
            />
            <MetaRow
              label={t("meta.updated")}
              value={
                document.updatedAt
                  ? new Date(document.updatedAt).toLocaleString()
                  : "—"
              }
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function PlainTextView({
  text,
  emptyLabel,
}: {
  text: string | null;
  emptyLabel: string;
}) {
  if (!text || !text.trim()) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        {emptyLabel}
      </p>
    );
  }
  return (
    <pre className="whitespace-pre-wrap wrap-break-word rounded-lg border bg-muted/30 p-4 font-mono text-sm leading-relaxed text-foreground/90">
      {text}
    </pre>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center gap-4">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
        <FileText className="h-10 w-10 text-muted-foreground" />
      </div>
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
      </div>
    </div>
  );
}

function MetaRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="block text-xs text-muted-foreground">{label}</span>
      <div className={cn("text-sm mt-1 break-all", mono && "font-mono")}>
        {value}
      </div>
    </div>
  );
}
