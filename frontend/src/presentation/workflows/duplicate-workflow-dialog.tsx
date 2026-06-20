"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useDuplicateWorkflowMutation } from "@/src/application/hooks/queries/workflows";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
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
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

interface DuplicateWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowUuid: string;
  workflowName: string;
}

export function DuplicateWorkflowDialog({
  open,
  onOpenChange,
  workflowUuid,
  workflowName,
}: DuplicateWorkflowDialogProps) {
  const t = useTranslations("Workflows.card");
  const router = useRouter();
  const mutation = useDuplicateWorkflowMutation();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Pre-rellena con "<nombre> (copia)" cada vez que se abre el diálogo.
  useEffect(() => {
    if (open) {
      setName(`${workflowName} ${t("duplicateDefaultSuffix")}`);
      setError(null);
    }
  }, [open, workflowName, t]);

  function submit() {
    setError(null);
    mutation.mutate(
      { uuid: workflowUuid, name: name.trim() },
      {
        onSuccess: (data) => {
          onOpenChange(false);
          router.push(`/workflows/${data.uuid}/document-types`);
        },
        onError: () => {
          setError(t("duplicateError"));
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-md p-6">
        <DialogHeader>
          <DialogTitle>{t("duplicateTitle")}</DialogTitle>
          <DialogDescription>
            {t("duplicateDescription", { name: workflowName })}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="duplicate-workflow-name">
              {t("duplicateNameLabel")}
            </Label>
            <Input
              id="duplicate-workflow-name"
              value={name}
              onValueChange={(v) => setName(v)}
            />
          </div>
          {error && (
            <div
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {error}
            </div>
          )}
        </DialogBody>
        <DialogFooter className="pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            {t("cancel")}
          </Button>
          <ActionButton
            type="button"
            loading={mutation.isPending}
            disabled={!name.trim()}
            onClick={submit}
          >
            {t("duplicateConfirm")}
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
