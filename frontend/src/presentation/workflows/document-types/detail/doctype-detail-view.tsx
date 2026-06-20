"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Pencil, Save } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { queryKeys } from "@/src/application/hooks/queries/keys";
import { useDoctypeEvents } from "@/src/application/hooks/use-doctype-events";
import { useDoctypeTaskActions } from "@/src/application/hooks/use-doctype-task-actions";
import { stripMarkdown } from "@/src/application/lib/strip-markdown";
import { useDocumentTypeSchemaStore } from "@/src/application/stores/doctype-schema-store";
import type { DocumentType } from "@/src/domain/entities/doctype";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpDocumentTypeRepository } from "@/src/infrastructure/repositories/http-doctype";
import { Button } from "@/src/presentation/components/ui/button";
import {
  FullPageSpinner,
  Spinner,
} from "@/src/presentation/components/ui/spinner";
import { DocumentTypeConfigPanel } from "../panels/doctype-config";
import { DocumentTypePreviewPanel } from "../panels/doctype-preview";

const doctypeRepository = new HttpDocumentTypeRepository(authHttp);

interface DocumentTypeDetailViewProps {
  doctypeId: string;
}

export function DocumentTypeDetailView({
  doctypeId,
}: DocumentTypeDetailViewProps) {
  const t = useTranslations("DoctypeDetail");
  const router = useRouter();
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const queryClient = useQueryClient();
  const invalidateDoctypeQueries = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: queryKeys.documentTypes.all(wfSlug),
    });
    queryClient.invalidateQueries({
      queryKey: queryKeys.documentTypes.detail(doctypeId),
    });
  }, [queryClient, wfSlug, doctypeId]);
  const [doctype, setDoctype] = useState<DocumentType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const nameInputRef = useRef<HTMLInputElement>(null);
  const [savingAction, setSavingAction] = useState<
    "save" | "saveAndClose" | null
  >(null);
  const [justSaved, setJustSaved] = useState(false);

  const loadDocType = useCallback(async () => {
    setIsLoading(true);
    const response = await doctypeRepository.getById(doctypeId);
    if ("data" in response) {
      setDoctype(response.data);
    }
    setIsLoading(false);
  }, [doctypeId]);

  useEffect(() => {
    loadDocType();
  }, [loadDocType]);

  useEffect(() => {
    if (doctype) setNameValue(doctype.name || "");
  }, [doctype]);

  useEffect(() => {
    if (!doctype) return;
    if (doctype.sampleFileText) completeTaskFor("doctype-text");
    const hasFields = doctype.fields && Object.keys(doctype.fields).length > 0;
    if (hasFields) completeTaskFor("doctype-fields");
  }, [doctype, doctypeId]);

  const [sseKey, setSseKey] = useState(0);
  const { startTaskFor, completeTaskFor, errorTaskFor } =
    useDoctypeTaskActions(doctypeId);

  useDoctypeEvents(
    doctypeId,
    {
      onSampleTextExtracted: () => {
        void loadDocType();
        completeTaskFor("doctype-text");
      },
      onSampleTextFailed: errorTaskFor(
        "doctype-text",
        t("tasks.extractTextError")
      ),
      onFieldsSuggested: () => {
        void loadDocType();
        completeTaskFor("doctype-fields");
      },
      onFieldsSuggestionFailed: errorTaskFor(
        "doctype-fields",
        t("tasks.fieldGenerationFailed")
      ),
    },
    sseKey
  );

  const handleNameBlur = async () => {
    setEditingName(false);
    const trimmed = (nameValue || "").trim();
    if (!trimmed || trimmed === doctype?.name) {
      setNameValue(doctype?.name || "");
      return;
    }
    const response = await doctypeRepository.update(doctypeId, {
      name: trimmed,
    });
    if ("data" in response) {
      setDoctype(response.data);
      invalidateDoctypeQueries();
    }
  };

  const saveDocType = async () => {
    const currentSchema = useDocumentTypeSchemaStore.getState().jsonSchema;
    // The backend rejects a schema with empty `properties`. Only send `fields`
    // when at least one field is defined; otherwise just persist the metadata
    // so "Guardar"/"Guardar y cerrar" work on a doc type without fields yet.
    const hasFields =
      !!currentSchema?.properties &&
      Object.keys(currentSchema.properties).length > 0;
    const response = await doctypeRepository.update(doctypeId, {
      name: (nameValue || "").trim() || doctype?.name,
      ...(hasFields
        ? { fields: currentSchema as Record<string, unknown> }
        : {}),
    });
    if ("data" in response) {
      setDoctype(response.data);
      invalidateDoctypeQueries();
    }
    return response;
  };

  const handlePersistValidationRules = useCallback(
    async (
      rules: import("@/src/domain/repositories/doctype").ValidationRulePayload[]
    ) => {
      const response = await doctypeRepository.update(doctypeId, {
        validationRules: rules,
      });
      if (!("data" in response)) {
        const msg = response.errors?.[0]?.message || t("errors.rulesRejected");
        throw new Error(msg);
      }
      setDoctype(response.data);
      invalidateDoctypeQueries();
    },
    [doctypeId, invalidateDoctypeQueries]
  );

  const handlePersistImport = useCallback(async () => {
    const currentSchema = useDocumentTypeSchemaStore.getState().jsonSchema;
    const response = await doctypeRepository.update(doctypeId, {
      fields: currentSchema as Record<string, unknown>,
    });
    if (!("data" in response)) {
      const msg = response.errors?.[0]?.message || t("errors.schemaRejected");
      throw new Error(msg);
    }
    setDoctype(response.data);
    invalidateDoctypeQueries();
    await loadDocType();
  }, [doctypeId, loadDocType, invalidateDoctypeQueries]);

  const handleFullImport = useCallback(
    async (
      payload: import("@/src/domain/repositories/doctype").UpdateDocumentTypePayload
    ) => {
      const response = await doctypeRepository.update(doctypeId, payload);
      if (!("data" in response)) {
        const msg = response.errors?.[0]?.message || t("errors.importRejected");
        throw new Error(msg);
      }
      setDoctype(response.data);
      invalidateDoctypeQueries();
      const importedFields = response.data.fields;
      if (importedFields && Object.keys(importedFields).length > 0) {
        useDocumentTypeSchemaStore
          .getState()
          .initializeFromSchema(
            doctypeId,
            importedFields as import("@/src/application/use-cases/json-schema/doctype-schema-converter").JsonSchemaNode
          );
      }
      await loadDocType();
    },
    [doctypeId, loadDocType, invalidateDoctypeQueries, t]
  );

  const handleDelete = useCallback(async () => {
    const response = await doctypeRepository.delete(doctypeId, wfSlug);
    if ("errors" in response) {
      const msg = response.errors?.[0]?.message || t("errors.deleteFailed");
      throw new Error(msg);
    }
    invalidateDoctypeQueries();
    router.push(`/workflows/${wfSlug}/document-types`);
  }, [doctypeId, wfSlug, router, invalidateDoctypeQueries, t]);

  const handleSave = async () => {
    setSavingAction("saveAndClose");
    try {
      const response = await saveDocType();
      if (response && "data" in response) {
        router.push(`/workflows/${wfSlug}/document-types`);
        return; // keep the loader on while we navigate away
      }
    } catch {
      // fall through to reset the button state
    }
    setSavingAction(null);
  };

  const handleSaveAndEdit = async () => {
    setSavingAction("save");
    try {
      const response = await saveDocType();
      if (response && "data" in response) {
        setJustSaved(true);
        setTimeout(() => setJustSaved(false), 2000);
      }
    } finally {
      setSavingAction(null);
    }
  };

  const descriptionText = useMemo(
    () => stripMarkdown(doctype?.description),
    [doctype?.description]
  );

  const handleSampleFileUploaded = () => {
    startTaskFor(
      "doctype-text",
      "Extrayendo texto del documento…",
      doctype?.name
    );
    setSseKey((k) => k + 1);
  };

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!doctype) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">{t("notFound")}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
            aria-label={t("backAria")}
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex flex-col">
            {editingName ? (
              <input
                ref={nameInputRef}
                type="text"
                value={nameValue ?? ""}
                onChange={(e) => setNameValue(e.target.value)}
                onBlur={handleNameBlur}
                onKeyDown={(e) => {
                  if (e.key === "Enter") nameInputRef.current?.blur();
                  if (e.key === "Escape") {
                    setNameValue(doctype.name);
                    setEditingName(false);
                  }
                }}
                placeholder={t("untitled")}
                className="text-xl font-mono bg-transparent border-b-2 border-primary outline-none px-1 py-0.5"
                autoFocus
              />
            ) : (
              <h1
                className="text-xl font-mono cursor-pointer hover:text-muted-foreground transition-colors flex items-center gap-2"
                onClick={() => {
                  setEditingName(true);
                  setTimeout(() => nameInputRef.current?.focus(), 0);
                }}
              >
                {doctype.name || t("untitled")}
                <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
              </h1>
            )}
            {descriptionText && (
              <p
                className="text-sm text-muted-foreground line-clamp-1"
                title={descriptionText}
              >
                {descriptionText}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {justSaved && (
            <span className="flex items-center gap-1.5 text-green-500 text-sm font-medium">
              <Check className="h-4 w-4" />
              {t("changesSaved")}
            </span>
          )}
          <Button
            variant="outline"
            className="gap-2"
            onClick={handleSaveAndEdit}
            disabled={savingAction !== null}
          >
            {savingAction === "save" ? (
              <Spinner size="xs" variant="muted" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {t("save")}
          </Button>
          <Button
            className="gap-2"
            onClick={handleSave}
            disabled={savingAction !== null}
          >
            {savingAction === "saveAndClose" ? (
              <Spinner size="xs" className="border-white/30 border-t-white" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {t("saveAndClose")}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 min-h-0">
        {/* Left Side - Metadata: fixed to viewport height, scrolls internally */}
        <div className="hidden md:flex md:w-1/3 lg:w-1/3 overflow-y-auto border-r">
          <DocumentTypeConfigPanel
            doctype={doctype}
            onUpdate={loadDocType}
            onSave={async (payload) => {
              const response = await doctypeRepository.update(
                doctypeId,
                payload
              );
              if ("data" in response) {
                setDoctype(response.data);
                invalidateDoctypeQueries();
              }
            }}
            onImport={handleFullImport}
            onDelete={handleDelete}
            onPersistImport={handlePersistImport}
            onPersistValidationRules={handlePersistValidationRules}
            onSuggestFieldsStarted={() => setSseKey((k) => k + 1)}
          />
        </div>

        {/* Right Side - Preview: scrolls with full document height */}
        <div className="flex-1 overflow-y-auto">
          <DocumentTypePreviewPanel
            doctype={doctype}
            onUpdate={loadDocType}
            onSampleFileUploaded={handleSampleFileUploaded}
          />
        </div>
      </div>
    </div>
  );
}
