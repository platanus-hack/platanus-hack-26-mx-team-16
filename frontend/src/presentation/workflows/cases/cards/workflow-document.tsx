"use client";

import {
  Eye,
  FileText,
  MoreVertical,
  Scissors,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Spinner } from "src/presentation/components/ui/spinner";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { CaseDocument } from "src/domain/entities/case";
import { CaseDocumentStatus } from "src/domain/entities/case";
import type { DocumentType } from "src/domain/entities/doctype";
import { authHttp } from "src/infrastructure/http/client";
import { HttpCaseRepository } from "src/infrastructure/repositories/http-case";
import { ConfirmDeleteDialog } from "src/presentation/components/common/confirm-delete-dialog";
import { shortUuid } from "src/application/lib/short-uuid";
import { Badge } from "src/presentation/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "src/presentation/components/ui/dropdown-menu";
import { docStatusConfig } from "../doc-status-config";

const PdfThumbnail = dynamic(
  () => import("../pdf-thumbnail").then((m) => m.PdfThumbnail),
  {
    ssr: false,
    loading: () => <Spinner size="sm" variant="muted" />,
  }
);

const caseRepository = new HttpCaseRepository(authHttp);

interface WorkflowDocumentCardProps {
  workflowUuid: string;
  caseId: string;
  documentType: DocumentType;
  document: CaseDocument;
  /** True while the document's WorkflowProcessingJob is being re-extracted. */
  isReExtracting?: boolean;
  onDocumentsChanged: () => Promise<void>;
}

const dateFormatter = new Intl.DateTimeFormat("es", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

function formatCreatedAt(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return dateFormatter.format(date);
}

// Wide pastel palette — 30 entries spanning the hue wheel with two
// lightness variants per family. Static class strings so Tailwind's JIT
// can pick them up at build time. The card hashes its `uuid` (FNV-1a) to
// select an entry, so collisions across a stack of N documents are
// vanishingly rare for small N (~30 ≫ usual stack depth).
// Both light and dark variants are FULLY OPAQUE so a card in front of the
// stack hides the ones behind it. Using `/N` opacity in dark mode caused
// the stacked cards to bleed into each other and look muddy on dark
// backgrounds (see screenshot Apr-28). The light side stays at `-50`,
// the dark side uses `-950` for primary swatches and `-900` for the
// alternate variant — both opaque, hue-tinted, and visually subtle.
const PASTEL_PALETTE = [
  "bg-rose-50 dark:bg-rose-950",
  "bg-rose-100 dark:bg-rose-900",
  "bg-pink-50 dark:bg-pink-950",
  "bg-pink-100 dark:bg-pink-900",
  "bg-fuchsia-50 dark:bg-fuchsia-950",
  "bg-fuchsia-100 dark:bg-fuchsia-900",
  "bg-purple-50 dark:bg-purple-950",
  "bg-purple-100 dark:bg-purple-900",
  "bg-violet-50 dark:bg-violet-950",
  "bg-violet-100 dark:bg-violet-900",
  "bg-indigo-50 dark:bg-indigo-950",
  "bg-indigo-100 dark:bg-indigo-900",
  "bg-blue-50 dark:bg-blue-950",
  "bg-blue-100 dark:bg-blue-900",
  "bg-sky-50 dark:bg-sky-950",
  "bg-sky-100 dark:bg-sky-900",
  "bg-cyan-50 dark:bg-cyan-950",
  "bg-cyan-100 dark:bg-cyan-900",
  "bg-teal-50 dark:bg-teal-950",
  "bg-teal-100 dark:bg-teal-900",
  "bg-emerald-50 dark:bg-emerald-950",
  "bg-emerald-100 dark:bg-emerald-900",
  "bg-green-50 dark:bg-green-950",
  "bg-green-100 dark:bg-green-900",
  "bg-lime-50 dark:bg-lime-950",
  "bg-lime-100 dark:bg-lime-900",
  "bg-yellow-50 dark:bg-yellow-950",
  "bg-amber-50 dark:bg-amber-950",
  "bg-amber-100 dark:bg-amber-900",
  "bg-orange-50 dark:bg-orange-950",
  "bg-orange-100 dark:bg-orange-900",
  "bg-red-50 dark:bg-red-950",
] as const;

function pastelClassFromUuid(uuid: string): string {
  // FNV-1a 32-bit — better avalanche than the prior `*31 + c` rolling
  // hash, so two uuids that differ in only one nibble land far apart in
  // the palette.
  let hash = 0x811c9dc5;
  for (let i = 0; i < uuid.length; i++) {
    hash ^= uuid.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  const idx = (hash >>> 0) % PASTEL_PALETTE.length;
  return PASTEL_PALETTE[idx];
}

export function WorkflowDocumentCard({
  workflowUuid,
  caseId,
  documentType,
  document,
  isReExtracting = false,
  onDocumentsChanged,
}: WorkflowDocumentCardProps) {
  const router = useRouter();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState<
    "idle" | "starting" | "running" | "completed" | "failed"
  >("idle");

  const openDocumentDetail = useCallback(() => {
    router.push(`/workflows/${workflowUuid}/documents/${document.uuid}`);
  }, [document.uuid, router, workflowUuid]);

  useEffect(() => {
    if (
      document.extraction &&
      Object.keys(document.extraction as Record<string, unknown>).length > 0
    ) {
      setExtractionStatus("completed");
    }
  }, [document.extraction]);

  const handleExtract = async () => {
    setExtractionStatus("starting");
    const res = await caseRepository.startCaseDocumentExtraction(
      workflowUuid,
      caseId,
      document.uuid
    );
    if (!("data" in res)) {
      setExtractionStatus("failed");
      return;
    }
    setExtractionStatus("running");
  };

  const status = document.status;
  const config = docStatusConfig[status];

  const docIsProcessing =
    status === CaseDocumentStatus.UPLOADED ||
    status === CaseDocumentStatus.PROCESSING ||
    extractionStatus === "starting" ||
    extractionStatus === "running" ||
    isReExtracting;

  useEffect(() => {
    if (!document.fileId) return;
    caseRepository.getFilePresignedUrl(document.fileId).then((res) => {
      if ("data" in res && res.data.presignedUrl) {
        setPreviewUrl(res.data.presignedUrl);
      }
    });
  }, [document.fileId]);

  const handleDelete = async () => {
    await caseRepository.deleteCaseDocument(
      workflowUuid,
      caseId,
      document.uuid
    );
    await onDocumentsChanged();
  };

  const isImage = Boolean(
    document.fileName?.match(/\.(png|jpg|jpeg|gif|webp)$/i)
  );
  const isPdf = Boolean(document.fileName?.match(/\.pdf$/i));
  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);

  useEffect(() => {
    if (!document.fileId || !isPdf) {
      setPdfData(null);
      return;
    }
    let cancelled = false;
    authHttp
      .get(`/documents/${document.fileId}/download`, {
        responseType: "arraybuffer",
      })
      .then((res) => {
        if (!cancelled) setPdfData(new Uint8Array(res.data as ArrayBuffer));
      })
      .catch(() => {
        if (!cancelled) setPdfData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [document.fileId, isPdf]);

  const shortDocUuid = shortUuid(document.uuid);
  const createdAtLabel = formatCreatedAt(document.createdAt);
  const pastelBg = pastelClassFromUuid(document.uuid);
  const pageRangeLabel = document.pageRange
    ? document.pageRange.from === document.pageRange.to
      ? `Pag. ${document.pageRange.from}`
      : `Pag. ${document.pageRange.from} - ${document.pageRange.to}`
    : null;

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={openDocumentDetail}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openDocumentDetail();
          }
        }}
        aria-label={`Abrir detalle de ${documentType.name}`}
        className={`
        relative rounded-xl border border-border/50 ${pastelBg}
        p-4 flex flex-col gap-3 cursor-pointer
        shadow-[0_1px_2px_rgba(0,0,0,0.04),0_4px_12px_-6px_rgba(0,0,0,0.08)]
        transition-shadow hover:shadow-md
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40
      `}
      >
        {/* Paper-like top tape strip — the visual signature that separates a
          loaded document card from the empty `DocumentTypeCard`. */}
        <span
          aria-hidden
          className="
          pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2
          h-2 w-12 rounded-full bg-foreground/5 backdrop-blur-sm
          shadow-[0_1px_0_0_rgba(0,0,0,0.04)]
        "
        />
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1 flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/80">
              {shortDocUuid}
            </span>
            <h3 className="truncate text-sm font-semibold leading-tight">
              {documentType.name}
            </h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={config.variant} className="gap-1 rounded-md">
              {docIsProcessing ? (
                <Spinner size="xs" />
              ) : (
                <config.icon className="h-3 w-3" />
              )}
              {config.label}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger
                aria-label="Acciones del documento"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center justify-center h-8 w-8 rounded-md cursor-pointer text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 transition-colors"
              >
                <MoreVertical className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                {/* Radix renders the menu in a DOM portal, but React events
                  still bubble through the JSX tree — without
                  stopPropagation each item click would also fire the
                  card's onClick and navigate to the document detail. */}
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    openDocumentDetail();
                  }}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  Ver
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={!isPdf}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Scissors className="mr-2 h-4 w-4" />
                  Dividir
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExtract();
                  }}
                  disabled={
                    extractionStatus === "starting" ||
                    extractionStatus === "running"
                  }
                >
                  {extractionStatus === "starting" ||
                  extractionStatus === "running" ? (
                    <Spinner size="xs" className="mr-2" />
                  ) : (
                    <Sparkles className="mr-2 h-4 w-4" />
                  )}
                  Extraer
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  variant="destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDeleteConfirm(true);
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Eliminar
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div
          className="
          group relative rounded-lg overflow-hidden
          bg-white dark:bg-zinc-900
          ring-1 ring-inset ring-border/60 dark:ring-white/5
          shadow-[inset_0_1px_2px_rgba(0,0,0,0.04)]
          min-h-[140px] flex items-center justify-center
        "
        >
          {previewUrl && isImage ? (
            <img
              src={previewUrl}
              alt={document.fileName ?? ""}
              className="w-full h-[140px] object-contain"
            />
          ) : pdfData && isPdf ? (
            <div className="w-full h-[140px] flex items-center justify-center overflow-hidden bg-white">
              <PdfThumbnail data={pdfData} height={140} />
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] w-full">
              <FileText className="h-12 w-12 text-muted-foreground/40" />
            </div>
          )}

          {docIsProcessing && (
            <div
              role="status"
              aria-live="polite"
              className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-background/70 backdrop-blur-[1px] text-foreground"
            >
              <Spinner size="sm" />
              <span className="text-xs font-medium">Procesando…</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground tabular-nums">
          {createdAtLabel ? <span>{createdAtLabel}</span> : <span />}
          {pageRangeLabel ? <span>{pageRangeLabel}</span> : null}
        </div>
      </div>

      {/* Rendered as a sibling of the card so AlertDialog clicks don't bubble
        through the React tree to the card's onClick. */}
      <ConfirmDeleteDialog
        open={showDeleteConfirm}
        onOpenChange={(open) => {
          if (!open) setShowDeleteConfirm(false);
        }}
        onConfirm={async () => {
          setShowDeleteConfirm(false);
          await handleDelete();
        }}
        title="Eliminar documento"
        description={`¿Eliminar "${documentType.name}"? Esta acción no se puede deshacer.`}
      />
    </>
  );
}
