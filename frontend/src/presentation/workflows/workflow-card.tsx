"use client";

import {
  Copy,
  CopyPlus,
  FileText,
  MoreVertical,
  Pencil,
  Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { Workflow } from "@/src/domain/entities/workflow";
import { hasCapability } from "@/src/domain/entities/workflow";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { DuplicateWorkflowDialog } from "@/src/presentation/workflows/duplicate-workflow-dialog";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";

interface WorkflowCardProps {
  workflow: Workflow;
  onEdit: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}

export function WorkflowCard({
  workflow,
  onEdit,
  onDelete,
}: WorkflowCardProps) {
  const t = useTranslations("Workflows.card");
  const router = useRouter();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showDuplicateDialog, setShowDuplicateDialog] = useState(false);
  const { hasPermission } = usePermissions();
  const canUpdate = hasPermission("workflows.update");
  const canDelete = hasPermission("workflows.delete");
  // Duplicar crea un workflow nuevo: se gobierna con el permiso de creación.
  const canCreate = hasPermission("workflows.create");

  const handleCardClick = (e: React.MouseEvent) => {
    if (
      (e.target as HTMLElement).closest('[role="menu"]') ||
      (e.target as HTMLElement).closest("button")
    ) {
      return;
    }
    // E7 · F1 (caso universal): «Casos» es la vista por defecto de todo workflow.
    router.push(`/workflows/${workflow.uuid}/cases`);
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(workflow.uuid);
  };

  const docTypeCount = workflow.selectedDocTypes.length;

  return (
    <>
      <Card
        className="cursor-pointer transition-all duration-300 hover:shadow-md hover:border-primary/20 hover:bg-muted/20"
        onClick={handleCardClick}
      >
        <CardHeader>
          <div className="flex flex-col gap-1.5">
            <CardTitle>{workflow.name}</CardTitle>
            {/* E7 · F2: badge derivado de capacidad (no de `workflowType`). */}
            <Badge
              variant="outline"
              className={`w-fit text-[10px] uppercase tracking-wider font-medium ${
                hasCapability(workflow, "analysis")
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400"
                  : "border-primary/40 bg-primary/10 text-primary"
              }`}
            >
              {hasCapability(workflow, "analysis") ? "Análisis" : "Extracción"}
            </Badge>
          </div>
          <CardAction>
            <DropdownMenu>
              <DropdownMenuTrigger
                className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreVertical className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  onClick={() => onEdit(workflow.uuid)}
                  disabled={!canUpdate}
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  {t("edit")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleCopyId()}>
                  <Copy className="mr-2 h-4 w-4" />
                  {t("copyId")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => setShowDuplicateDialog(true)}
                  disabled={!canCreate}
                >
                  <CopyPlus className="mr-2 h-4 w-4" />
                  {t("duplicate")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() => setShowDeleteDialog(true)}
                  disabled={!canDelete}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            {docTypeCount > 0 ? (
              <Badge variant="secondary" className="gap-1.5 font-normal">
                <FileText className="h-3 w-3" />
                {docTypeCount === 1
                  ? t("docTypeOne", { count: docTypeCount })
                  : t("docTypeOther", { count: docTypeCount })}
              </Badge>
            ) : (
              <span className="text-sm text-muted-foreground italic">
                {t("noDocTypes")}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      <ConfirmDeleteDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={() => onDelete(workflow.uuid)}
        title={t("deleteTitle")}
        description={t("deleteDescription", { name: workflow.name })}
        confirmLabel={t("confirmDelete")}
        cancelLabel={t("cancel")}
      />

      <DuplicateWorkflowDialog
        open={showDuplicateDialog}
        onOpenChange={setShowDuplicateDialog}
        workflowUuid={workflow.uuid}
        workflowName={workflow.name}
      />
    </>
  );
}
