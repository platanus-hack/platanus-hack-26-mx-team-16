"use client";

import { AlertCircle, FileJson } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import type { UpdateDocumentTypePayload } from "@/src/domain/repositories/doctype";
import { httpDocumentTypeRepository } from "@/src/infrastructure/repositories/http-doctype";
import { Button } from "@/src/presentation/components/ui/button";
import { parseDoctypeImport, schemaHasFields } from "./doctype-import";
import { type ImportChange, ImportDoctypeModal } from "./import-doctype-modal";

interface PendingImport {
  payload: UpdateDocumentTypePayload;
  changes: ImportChange[];
}

/**
 * "Import JSON" action for the document-types list. Unlike the settings-tab
 * import (which overwrites the current document type), this always *creates* a
 * new one: the backend assigns a fresh uuid and a unique slug, so any id/slug in
 * the file is ignored and cannot collide on the database primary key.
 */
export function ImportDoctypeButton() {
  const t = useTranslations("WorkflowConfig");
  const tImport = useTranslations("DoctypeSettingsTab");
  const router = useRouter();
  const params = useParams();
  const wfSlug = params.wfSlug as string;

  const inputRef = useRef<HTMLInputElement>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingImport | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(
    () => () => {
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    },
    []
  );

  const showError = useCallback((message: string) => {
    setError(message);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => setError(null), 6000);
  }, []);

  const handleClick = useCallback(() => {
    setError(null);
    inputRef.current?.click();
  }, []);

  const handleFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      setError(null);

      let raw: unknown;
      try {
        raw = JSON.parse(await file.text());
      } catch {
        showError(tImport("importErrorInvalidJson"));
        return;
      }

      const result = parseDoctypeImport(raw, tImport);
      if (!result.ok) {
        showError(result.error);
        return;
      }

      setPending({ payload: result.payload, changes: result.changes });
      setModalOpen(true);
    },
    [showError, tImport]
  );

  const handleConfirm = useCallback(async () => {
    if (!pending) return;
    const { payload } = pending;

    // Step 1: create a fresh document type (new uuid + unique slug server-side).
    const created = await httpDocumentTypeRepository.create(
      {
        name: payload.name?.trim() || "Untitled",
        description: payload.description,
      },
      wfSlug
    );
    if (!("data" in created)) {
      throw new Error(
        created.errors?.[0]?.message ?? tImport("importErrorCreateFailed")
      );
    }
    const newId = created.data.uuid;

    // Step 2: apply the fields the create endpoint doesn't accept (keywords,
    // examples, validation rules, schema). Drop an empty schema so the backend's
    // "at least one field" invariant doesn't reject the request.
    const updatePayload: UpdateDocumentTypePayload = {
      keywords: payload.keywords,
      examples: payload.examples,
      validationRules: payload.validationRules,
    };
    if (schemaHasFields(payload.fields)) {
      updatePayload.fields = payload.fields;
    }
    if (Object.values(updatePayload).some((value) => value !== undefined)) {
      const updated = await httpDocumentTypeRepository.update(
        newId,
        updatePayload
      );
      if (!("data" in updated)) {
        throw new Error(
          updated.errors?.[0]?.message ?? tImport("importErrorCreateFailed")
        );
      }
    }

    setModalOpen(false);
    setPending(null);
    router.push(`/workflows/${wfSlug}/document-types/${newId}`);
  }, [pending, wfSlug, router, tImport]);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={handleFile}
      />
      <Button variant="outline" className="gap-2" onClick={handleClick}>
        <FileJson className="h-4 w-4" />
        {t("actions.importJson")}
      </Button>

      <ImportDoctypeModal
        open={modalOpen}
        mode="create"
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) setPending(null);
        }}
        changes={pending?.changes ?? []}
        onConfirm={handleConfirm}
      />

      {error && (
        <div
          role="alert"
          className="fixed bottom-4 right-4 z-50 flex max-w-sm items-start gap-2 rounded-md border border-destructive/30 bg-background px-3 py-2 text-xs text-destructive shadow-md"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </>
  );
}
