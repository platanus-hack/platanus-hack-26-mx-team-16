"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";

interface ConfirmReplaceDocumentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  hasFields: boolean;
  hasExtractedText: boolean;
}

export function ConfirmReplaceDocumentDialog({
  open,
  onOpenChange,
  onConfirm,
  hasFields,
  hasExtractedText,
}: ConfirmReplaceDocumentDialogProps) {
  const t = useTranslations("ConfirmReplaceDocument");

  const parts: string[] = [];
  if (hasExtractedText) parts.push(t("extractedText"));
  if (hasFields) parts.push(t("configuredFields"));
  const items =
    parts.length === 2 ? `${parts[0]} ${t("and")} ${parts[1]}` : parts[0] ?? "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-sm p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>
        <div className="py-4 text-sm text-muted-foreground">
          <p>{t("message", { items })}</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("cancel")}
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {t("replace")}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
