"use client";

import {
  AlertCircle,
  Check,
  Copy,
  Download,
  Trash2,
  Upload,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import type { DocumentType } from "@/src/domain/entities/doctype";
import type { UpdateDocumentTypePayload } from "@/src/domain/repositories/doctype";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { Button } from "@/src/presentation/components/ui/button";
import { ExamplesEditor } from "@/src/presentation/components/ui/examples-editor";
import { Input } from "@/src/presentation/components/ui/input";
import { KeywordsInput } from "@/src/presentation/components/ui/keywords-input";
import { Label } from "@/src/presentation/components/ui/label";
import { MarkdownRichEditor } from "@/src/presentation/components/ui/markdown-rich-editor";
import { Spinner } from "@/src/presentation/components/ui/spinner";
import { parseDoctypeImport } from "@/src/presentation/workflows/document-types/detail/doctype-import";
import {
  type ImportChange,
  ImportDoctypeModal,
} from "@/src/presentation/workflows/document-types/detail/import-doctype-modal";

type SaveKey = "description" | "keywords" | "examples";

interface PendingImport {
  payload: UpdateDocumentTypePayload;
  changes: ImportChange[];
}

function arraysEqual(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

function slugify(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "") || "document-type"
  );
}

interface SettingsTabProps {
  doctype: DocumentType;
  onUpdate: () => void;
  onSave?: (payload: UpdateDocumentTypePayload) => Promise<void>;
  onImport?: (payload: UpdateDocumentTypePayload) => Promise<void>;
  onDelete?: () => Promise<void>;
}

export function DocumentTypeSettingsTab({
  doctype,
  onUpdate,
  onSave,
  onImport,
  onDelete,
}: SettingsTabProps) {
  const t = useTranslations("DoctypeSettingsTab");
  const [description, setDescription] = useState(doctype.description ?? "");
  const [keywords, setKeywords] = useState<string[]>(doctype.keywords ?? []);
  const [examples, setExamples] = useState<string[]>(doctype.examples ?? []);
  const [savingKey, setSavingKey] = useState<SaveKey | null>(null);

  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingImport, setPendingImport] = useState<PendingImport | null>(
    null
  );
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const importInputRef = useRef<HTMLInputElement>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDescription(doctype.description ?? "");
  }, [doctype.description]);

  useEffect(() => {
    setKeywords(doctype.keywords ?? []);
  }, [doctype.keywords]);

  useEffect(() => {
    setExamples(doctype.examples ?? []);
  }, [doctype.examples]);

  useEffect(() => {
    return () => {
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    };
  }, []);

  const showActionError = useCallback((message: string) => {
    setActionError(message);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => setActionError(null), 6000);
  }, []);

  const descriptionDirty = description !== (doctype.description ?? "");
  const keywordsDirty = !arraysEqual(keywords, doctype.keywords ?? []);
  const examplesDirty = !arraysEqual(examples, doctype.examples ?? []);

  const handleSave = async (
    key: SaveKey,
    payload: UpdateDocumentTypePayload
  ) => {
    if (!onSave) return;
    setSavingKey(key);
    try {
      await onSave(payload);
    } finally {
      setSavingKey(null);
    }
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(doctype.uuid);
  };

  const handleCopySlug = () => {
    if (doctype.slug) navigator.clipboard.writeText(doctype.slug);
  };

  const handleExport = useCallback(() => {
    const exportData = {
      name: doctype.name,
      slug: doctype.slug ?? null,
      description: doctype.description ?? "",
      keywords: doctype.keywords ?? [],
      examples: doctype.examples ?? [],
      fields: doctype.fields ?? { type: "object", properties: {} },
      validationRules: doctype.validationRules ?? [],
    };
    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${slugify(doctype.slug || doctype.name || "document-type")}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }, [doctype]);

  const handleImportClick = useCallback(() => {
    setActionError(null);
    importInputRef.current?.click();
  }, []);

  const handleImportFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      setActionError(null);

      let raw: unknown;
      try {
        raw = JSON.parse(await file.text());
      } catch {
        showActionError(t("importErrorInvalidJson"));
        return;
      }

      const result = parseDoctypeImport(raw, t);
      if (!result.ok) {
        showActionError(result.error);
        return;
      }

      setPendingImport({ payload: result.payload, changes: result.changes });
      setImportModalOpen(true);
    },
    [showActionError, t]
  );

  const handleConfirmImport = useCallback(async () => {
    if (!onImport || !pendingImport) return;
    await onImport(pendingImport.payload);
    setImportModalOpen(false);
    setPendingImport(null);
    onUpdate();
  }, [onImport, pendingImport, onUpdate]);

  const handleConfirmDelete = useCallback(() => {
    if (!onDelete) return;
    void (async () => {
      try {
        await onDelete();
      } catch (err) {
        showActionError(err instanceof Error ? err.message : t("deleteFailed"));
      }
    })();
  }, [onDelete, showActionError, t]);

  const renderSaveRow = (
    key: SaveKey,
    dirty: boolean,
    payload: UpdateDocumentTypePayload,
    hint?: string
  ) => (
    <div className="flex items-center justify-between">
      <p className="text-xs text-muted-foreground">{hint}</p>
      {savingKey === key && <Spinner size="xs" variant="muted" />}
      {savingKey !== key && dirty && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleSave(key, payload)}
          className="gap-1 h-7 text-xs"
        >
          <Check className="h-3 w-3" />
          {t("save")}
        </Button>
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      <input
        ref={importInputRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={handleImportFile}
      />

      <div className="flex-1 overflow-y-auto space-y-6 p-4">
        <div className="space-y-2">
          <Label className="text-sm font-medium">{t("idLabel")}</Label>
          <p className="text-xs text-muted-foreground">{t("idDescription")}</p>
          <div className="flex items-center gap-2">
            <Input
              value={doctype.uuid}
              readOnly
              className="font-mono text-sm bg-muted"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyId}
              className="flex-shrink-0"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">{t("slugLabel")}</Label>
          <p className="text-xs text-muted-foreground">
            {t("slugDescription")}
          </p>
          <div className="flex items-center gap-2">
            <Input
              value={doctype.slug ?? ""}
              readOnly
              placeholder="—"
              className="font-mono text-sm bg-muted"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopySlug}
              disabled={!doctype.slug}
              className="flex-shrink-0"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">{t("descriptionLabel")}</Label>
          <MarkdownRichEditor
            value={description}
            onChange={setDescription}
            placeholder={t("descriptionPlaceholder")}
            minHeight={140}
          />
          {renderSaveRow(
            "description",
            descriptionDirty,
            { description },
            t("descriptionHint")
          )}
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">{t("keywordsLabel")}</Label>
          <KeywordsInput
            value={keywords}
            onChange={setKeywords}
            placeholder={t("keywordsPlaceholder")}
          />
          {renderSaveRow(
            "keywords",
            keywordsDirty,
            { keywords },
            t("keywordsHint")
          )}
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">{t("examplesLabel")}</Label>
          <ExamplesEditor value={examples} onChange={setExamples} />
          {renderSaveRow(
            "examples",
            examplesDirty,
            { examples },
            t("examplesHint")
          )}
        </div>
      </div>

      {actionError && (
        <div
          role="alert"
          className="mx-4 mb-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      <div className="border-t border-border/50 p-3 flex items-center gap-2">
        <Button
          variant="outline"
          onClick={handleExport}
          aria-label={t("exportAria")}
          className="gap-2 flex-1"
        >
          <Download className="h-4 w-4" />
          {t("export")}
        </Button>
        <Button
          variant="outline"
          onClick={handleImportClick}
          aria-label={t("importAria")}
          className="gap-2 flex-1"
        >
          <Upload className="h-4 w-4" />
          {t("import")}
        </Button>
        <Button
          variant="outline"
          onClick={() => setDeleteOpen(true)}
          className="gap-2 flex-1 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
          {t("delete")}
        </Button>
      </div>

      <ImportDoctypeModal
        open={importModalOpen}
        onOpenChange={(open) => {
          setImportModalOpen(open);
          if (!open) setPendingImport(null);
        }}
        changes={pendingImport?.changes ?? []}
        onConfirm={handleConfirmImport}
      />

      <ConfirmDeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={handleConfirmDelete}
        title={t("deleteTitle")}
        description={t("deleteDescription", { name: doctype.name })}
        confirmLabel={t("deleteConfirm")}
        cancelLabel={t("deleteCancel")}
      />
    </div>
  );
}
