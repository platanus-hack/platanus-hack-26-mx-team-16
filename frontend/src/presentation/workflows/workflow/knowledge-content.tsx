"use client";

import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  File as FileIcon,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileType,
  MoreVertical,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  type MutableRefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { cn } from "@/src/application/lib/utils";
import type {
  KnowledgeDocument,
  KnowledgeDocumentStatus,
} from "@/src/domain/entities/knowledge-document";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpKnowledgeDocumentRepository } from "@/src/infrastructure/repositories/http-knowledge-document";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
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
import { Spinner } from "@/src/presentation/components/ui/spinner";

const ACCEPTED_MIMES =
  "application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/plain,text/markdown";
const ACCEPTED_EXTENSIONS = ".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.txt,.md";
const ACCEPTED_EXT_SET = new Set(ACCEPTED_EXTENSIONS.split(","));
const POLL_INTERVAL_MS = 2500;

const repository = new HttpKnowledgeDocumentRepository(authHttp);

interface KnowledgeContentProps {
  wfSlug: string;
  onUploadRef?: MutableRefObject<(() => void) | null>;
}

export function KnowledgeContent({
  wfSlug,
  onUploadRef,
}: KnowledgeContentProps) {
  const t = useTranslations("KnowledgeContent");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<KnowledgeDocument | null>(
    null
  );
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasVectorizing = useMemo(
    () => documents.some((d) => d.status === "vectorizing"),
    [documents]
  );

  const fetchDocuments = useCallback(async () => {
    const response = await repository.listByWorkflow(wfSlug);
    if ("data" in response) {
      setDocuments(response.data);
      setLoadError(null);
    } else {
      setLoadError(response.errors?.[0]?.message ?? t("loadError"));
    }
  }, [wfSlug, t]);

  useEffect(() => {
    setLoading(true);
    fetchDocuments().finally(() => setLoading(false));
  }, [fetchDocuments]);

  useEffect(() => {
    if (!hasVectorizing) {
      if (pollingRef.current) clearTimeout(pollingRef.current);
      return;
    }
    pollingRef.current = setTimeout(() => {
      fetchDocuments();
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollingRef.current) clearTimeout(pollingRef.current);
    };
  }, [hasVectorizing, documents, fetchDocuments]);

  const openFilePicker = useCallback(() => {
    setUploadError(null);
    fileInputRef.current?.click();
  }, []);

  useEffect(() => {
    if (!onUploadRef) return;
    onUploadRef.current = openFilePicker;
    return () => {
      onUploadRef.current = null;
    };
  }, [onUploadRef, openFilePicker]);

  const handleFileSelected = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) return;

    for (const file of files) {
      const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
      if (!ACCEPTED_EXT_SET.has(ext)) {
        setUploadError(
          t("unsupportedType", {
            name: file.name,
            allowed: ACCEPTED_EXTENSIONS,
          })
        );
        continue;
      }
      const response = await repository.uploadToWorkflow(wfSlug, file);
      if ("data" in response) {
        setDocuments((prev) => [response.data, ...prev]);
      } else {
        setUploadError(
          response.errors?.[0]?.message ??
            t("uploadFailed", { name: file.name })
        );
      }
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    const response = await repository.deleteFromWorkflow(
      wfSlug,
      pendingDelete.uuid
    );
    setDeleting(false);
    if ("errors" in response) {
      setUploadError(response.errors?.[0]?.message ?? t("deleteFailed"));
      return;
    }
    setDocuments((prev) => prev.filter((d) => d.uuid !== pendingDelete.uuid));
    setPendingDelete(null);
  };

  return (
    <div className="flex flex-1 flex-col gap-4 p-6 h-full overflow-auto">
      <input
        ref={fileInputRef}
        type="file"
        accept={`${ACCEPTED_MIMES},${ACCEPTED_EXTENSIONS}`}
        multiple
        className="hidden"
        onChange={handleFileSelected}
      />

      {uploadError && (
        <div className="flex items-center justify-between gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {uploadError}
          </span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setUploadError(null)}
          >
            {t("dismiss")}
          </Button>
        </div>
      )}

      {loading ? (
        <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
          <Spinner size="sm" variant="muted" />
          {t("loading")}
        </div>
      ) : loadError ? (
        <div className="flex flex-1 items-center justify-center text-destructive">
          {loadError}
        </div>
      ) : documents.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={BookOpen}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={t("upload")}
            onAction={openFilePicker}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <KbDocumentCard
              key={doc.uuid}
              document={doc}
              onDelete={() => {
                setTimeout(() => setPendingDelete(doc), 0);
              }}
            />
          ))}
        </div>
      )}

      <AlertDialog
        open={!!pendingDelete}
        onOpenChange={(open) => !open && setPendingDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription", { name: pendingDelete?.fileName ?? "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>
              {t("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                confirmDelete();
              }}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? t("deleting") : t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function KbDocumentCard({
  document,
  onDelete,
}: {
  document: KnowledgeDocument;
  onDelete: () => void;
}) {
  const t = useTranslations("KnowledgeContent");
  const locale = useLocale();
  const { Icon, tint } = getDocumentIcon(document.mime, document.fileName);
  const updated = document.updatedAt
    ? new Date(document.updatedAt).toLocaleString(
        locale === "es" ? "es-ES" : "en-US"
      )
    : "";

  return (
    <div
      data-testid="kb-document-card"
      data-status={document.status}
      className={cn(
        "group relative flex items-center gap-3 rounded-md border bg-card px-3 py-2 shadow-sm transition-colors hover:bg-accent/40",
        document.status === "vectorizing" && "border-primary/30",
        document.status === "failed" && "border-destructive/40"
      )}
    >
      {document.status === "vectorizing" && (
        <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden rounded-t-md bg-primary/10">
          <div className="h-full w-full animate-pulse bg-primary" />
        </div>
      )}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
          document.status === "failed"
            ? "bg-destructive/10 text-destructive"
            : tint
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1 pr-8">
        <p
          className="truncate text-sm font-medium leading-tight"
          title={document.fileName}
        >
          {document.fileName}
        </p>
        <div className="mt-1">
          <StatusBadge status={document.status} />
        </div>
        <p className="mt-1 truncate text-[10px] leading-tight text-muted-foreground">
          {updated}
        </p>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={t("optionsAria")}
          className="absolute right-1.5 top-1.5 inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <MoreVertical className="h-4 w-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem
            variant="destructive"
            onClick={onDelete}
            disabled={document.status === "vectorizing"}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t("delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function StatusBadge({ status }: { status: KnowledgeDocumentStatus }) {
  const t = useTranslations("KnowledgeContent.status");
  if (status === "vectorizing") {
    return (
      <Badge
        variant="secondary"
        className="h-5 shrink-0 gap-1 px-1.5 text-[10px] font-medium"
      >
        <Spinner size="xs" />
        {t("vectorizing")}
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge
        variant="destructive"
        className="h-5 shrink-0 gap-1 px-1.5 text-[10px] font-medium"
      >
        <AlertTriangle className="h-3 w-3" />
        {t("failed")}
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className="h-5 shrink-0 gap-1 border-emerald-500/40 px-1.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400"
    >
      <CheckCircle2 className="h-3 w-3" />
      {t("ready")}
    </Badge>
  );
}

function getDocumentIcon(
  mime: string,
  fileName: string
): { Icon: LucideIcon; tint: string } {
  const lowerMime = mime.toLowerCase();
  const ext = fileName.split(".").pop()?.toLowerCase() ?? "";

  if (lowerMime.includes("pdf") || ext === "pdf") {
    return {
      Icon: FileType,
      tint: "bg-red-500/10 text-red-600 dark:text-red-400",
    };
  }
  if (
    lowerMime.startsWith("image/") ||
    ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)
  ) {
    return {
      Icon: FileImage,
      tint: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    };
  }
  if (
    lowerMime.includes("spreadsheet") ||
    lowerMime.includes("excel") ||
    ["xlsx", "xls", "csv"].includes(ext)
  ) {
    return {
      Icon: FileSpreadsheet,
      tint: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    };
  }
  if (lowerMime.startsWith("text/") || ["txt", "md", "json"].includes(ext)) {
    return {
      Icon: FileText,
      tint: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
    };
  }
  return {
    Icon: FileIcon,
    tint: "bg-muted text-muted-foreground",
  };
}
