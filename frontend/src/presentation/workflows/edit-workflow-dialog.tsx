"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import type { CaseNoun, Workflow } from "@/src/domain/entities/workflow";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { ActionButton } from "@/src/presentation/components/ui/action-button";

interface EditWorkflowDialogProps {
  workflow: Workflow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    uuid: string,
    name: string,
    caseNoun: CaseNoun | null
  ) => Promise<void>;
}

const NOUN_MAX = 30;

export function EditWorkflowDialog({
  workflow,
  open,
  onOpenChange,
  onSubmit,
}: EditWorkflowDialogProps) {
  const t = useTranslations("Workflows.editDialog");
  const [name, setName] = useState("");
  const [esOne, setEsOne] = useState("");
  const [esOther, setEsOther] = useState("");
  const [enOne, setEnOne] = useState("");
  const [enOther, setEnOther] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (workflow && open) {
      setName(workflow.name);
      setEsOne(workflow.caseNoun?.es.one ?? "");
      setEsOther(workflow.caseNoun?.es.other ?? "");
      setEnOne(workflow.caseNoun?.en.one ?? "");
      setEnOther(workflow.caseNoun?.en.other ?? "");
    }
  }, [workflow, open]);

  const nounForms = [esOne, esOther, enOne, enOther].map((s) => s.trim());
  const filledCount = nounForms.filter(Boolean).length;
  const nounEmpty = filledCount === 0;
  const nounComplete = filledCount === 4;
  const nounValid = nounEmpty || nounComplete;

  const canSubmit = name.trim().length > 0 && nounValid && !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit || !workflow) return;
    const caseNoun: CaseNoun | null = nounComplete
      ? {
          es: { one: esOne.trim(), other: esOther.trim() },
          en: { one: enOne.trim(), other: enOther.trim() },
        }
      : null;
    setIsSubmitting(true);
    try {
      await onSubmit(workflow.uuid, name.trim(), caseNoun);
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-lg p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="edit-workflow-name">{t("nameLabel")}</Label>
            <Input
              id="edit-workflow-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
              }}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label>{t("caseNounLabel")}</Label>
            <p className="text-xs text-muted-foreground">{t("caseNounHelp")}</p>
            <div className="grid grid-cols-[auto_1fr_1fr] items-center gap-2">
              <span />
              <span className="text-xs font-medium text-muted-foreground">
                {t("singular")}
              </span>
              <span className="text-xs font-medium text-muted-foreground">
                {t("plural")}
              </span>

              <span className="text-sm text-muted-foreground">
                {t("langEs")}
              </span>
              <Input
                aria-label={`${t("langEs")} · ${t("singular")}`}
                value={esOne}
                maxLength={NOUN_MAX}
                placeholder="Caso"
                onChange={(e) => setEsOne(e.target.value)}
              />
              <Input
                aria-label={`${t("langEs")} · ${t("plural")}`}
                value={esOther}
                maxLength={NOUN_MAX}
                placeholder="Casos"
                onChange={(e) => setEsOther(e.target.value)}
              />

              <span className="text-sm text-muted-foreground">
                {t("langEn")}
              </span>
              <Input
                aria-label={`${t("langEn")} · ${t("singular")}`}
                value={enOne}
                maxLength={NOUN_MAX}
                placeholder="Case"
                onChange={(e) => setEnOne(e.target.value)}
              />
              <Input
                aria-label={`${t("langEn")} · ${t("plural")}`}
                value={enOther}
                maxLength={NOUN_MAX}
                placeholder="Cases"
                onChange={(e) => setEnOther(e.target.value)}
              />
            </div>
            {!nounEmpty && !nounComplete && (
              <p className="text-xs text-destructive">{t("caseNounError")}</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            {t("cancel")}
          </Button>
          <ActionButton
            onClick={handleSubmit}
            disabled={!canSubmit}
            loading={isSubmitting}
          >
            {t("submit")}
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
