"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Label } from "@/src/presentation/components/ui/label";
import { Textarea } from "@/src/presentation/components/ui/textarea";

interface SuggestFieldsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuggest: (prompt: string) => Promise<void>;
  hasExistingFields?: boolean;
}

export function SuggestFieldsModal({
  open,
  onOpenChange,
  onSuggest,
  hasExistingFields = true,
}: SuggestFieldsModalProps) {
  const t = useTranslations("SuggestFieldsModal");
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleOpenChange = (value: boolean) => {
    if (!value) {
      setPrompt("");
      setError(null);
    }
    onOpenChange(value);
  };

  const handleContinue = async () => {
    setError(null);
    try {
      await onSuggest(prompt.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorDefault"));
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-md p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-2">
            <Label>{t("descriptionLabel")}</Label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t("descriptionPlaceholder")}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              {t("descriptionHint")}
            </p>
          </div>
          {hasExistingFields && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <p className="text-xs">{t("existingFieldsWarning")}</p>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            {t("cancel")}
          </Button>
          <Button onClick={handleContinue}>{t("generate")}</Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
