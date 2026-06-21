"use client";

import { useTranslations } from "next-intl";

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

type ConfirmVariant = "destructive" | "primary";

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title?: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
}

const VARIANT_CLASS: Record<ConfirmVariant, string> = {
  destructive:
    "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  primary:
    "bg-primary-action text-primary-action-foreground hover:bg-primary-action/90",
};

export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmLabel,
  cancelLabel,
  variant = "destructive",
}: ConfirmDeleteDialogProps) {
  const t = useTranslations("ConfirmDelete");

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title ?? t("defaultTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {description ?? t("defaultDescription")}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>
            {cancelLabel ?? t("defaultCancel")}
          </AlertDialogCancel>
          <AlertDialogAction
            className={VARIANT_CLASS[variant]}
            onClick={onConfirm}
          >
            {confirmLabel ?? t("defaultConfirm")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
