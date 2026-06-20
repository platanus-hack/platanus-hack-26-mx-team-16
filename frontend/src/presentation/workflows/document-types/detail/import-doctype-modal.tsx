"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Spinner } from "@/src/presentation/components/ui/spinner";

export interface ImportChange {
  key: string;
  label: string;
  preview: string;
}

interface ImportDoctypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  changes: ImportChange[];
  onConfirm: () => Promise<void>;
  // "update" overwrites the current document type (settings tab); "create"
  // spins up a brand-new one from the list, so nothing is overwritten.
  mode?: "update" | "create";
}

export function ImportDoctypeModal({
  open,
  onOpenChange,
  changes,
  onConfirm,
  mode = "update",
}: ImportDoctypeModalProps) {
  const t = useTranslations("ImportDoctypeModal");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenChange = (value: boolean) => {
    if (submitting) return;
    if (!value) setError(null);
    onOpenChange(value);
  };

  const handleConfirm = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorDefault"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-md p-6">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? t("titleCreate") : t("title")}</DialogTitle>
          <DialogDescription>
            {mode === "create" ? t("descriptionCreate") : t("description")}
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="gap-3 py-2">
          {mode === "update" && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <p className="text-xs">{t("warning")}</p>
            </div>
          )}

          <ul className="flex flex-col divide-y divide-border/60 rounded-md border border-border/60">
            {changes.map((change) => (
              <li
                key={change.key}
                className="flex items-center justify-between gap-3 px-3 py-2"
              >
                <span className="text-sm font-medium text-foreground">
                  {change.label}
                </span>
                <span className="max-w-[55%] truncate text-right text-xs text-muted-foreground">
                  {change.preview}
                </span>
              </li>
            ))}
          </ul>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </DialogBody>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={submitting}
          >
            {t("cancel")}
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={submitting}
            className="gap-2"
          >
            {submitting && (
              <Spinner size="xs" className="border-white/30 border-t-white" />
            )}
            {mode === "create" ? t("confirmCreate") : t("confirm")}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
