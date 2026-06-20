"use client";

import { FolderOpen, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import {
  useCreateWorkflowFromYamlMutation,
  useCreateWorkflowMutation,
  useDeleteWorkflowMutation,
  useUpdateWorkflowMutation,
  useWorkflowsQuery,
} from "@/src/application/hooks/queries/workflows";
import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { CaseNoun, Workflow } from "@/src/domain/entities/workflow";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Button } from "@/src/presentation/components/ui/button";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
import {
  CreateWorkflowDialog,
  type CreateWorkflowSubmit,
} from "./create-workflow-dialog";
import { EditWorkflowDialog } from "./edit-workflow-dialog";
import { WorkflowCard } from "./workflow-card";

export function WorkflowsView() {
  const t = useTranslations("Workflows");
  const router = useRouter();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null);
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("workflows.create");

  const { data: workflows = [], isLoading, error } = useWorkflowsQuery();
  const createMutation = useCreateWorkflowMutation();
  const createFromYamlMutation = useCreateWorkflowFromYamlMutation();
  const updateMutation = useUpdateWorkflowMutation();
  const deleteMutation = useDeleteWorkflowMutation();

  const handleCreateSubmit = async ({
    name,
    templateSlug,
    yaml,
  }: CreateWorkflowSubmit) => {
    if (yaml) {
      // Alta desde plantilla YAML: el backend parsea + importa el bundle. Tras
      // crear, vamos al workflow para revisar tipos/pipeline/reglas importados.
      const created = await createFromYamlMutation.mutateAsync({ name, yaml });
      setShowCreateDialog(false);
      router.push(`/workflows/${created.uuid}/document-types`);
      return;
    }
    // E7 · F2: el alta manda el slug de la receta inicial (None ⇒ extracción).
    await createMutation.mutateAsync({ name, templateSlug });
    setShowCreateDialog(false);
  };

  const handleEdit = (uuid: string) => {
    const workflow = workflows.find((w) => w.uuid === uuid);
    if (workflow) setEditingWorkflow(workflow);
  };

  const handleEditSubmit = async (
    uuid: string,
    name: string,
    caseNoun: CaseNoun | null
  ) => {
    await updateMutation.mutateAsync({
      uuid,
      payload: caseNoun ? { name, caseNoun } : { name },
    });
    setEditingWorkflow(null);
  };

  const handleDelete = async (uuid: string) => {
    await deleteMutation.mutateAsync(uuid);
  };

  const dialogs = (
    <>
      <CreateWorkflowDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSubmit={handleCreateSubmit}
      />
      <EditWorkflowDialog
        workflow={editingWorkflow}
        open={editingWorkflow !== null}
        onOpenChange={(open) => {
          if (!open) setEditingWorkflow(null);
        }}
        onSubmit={handleEditSubmit}
      />
    </>
  );

  if (isLoading) return <FullPageSpinner />;

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-100">
        <div className="text-destructive">{error.message}</div>
      </div>
    );
  }

  if (workflows.length === 0) {
    return (
      <>
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={FolderOpen}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={canCreate ? t("create") : undefined}
            onAction={canCreate ? () => setShowCreateDialog(true) : undefined}
          />
        </div>
        {dialogs}
      </>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="gap-2"
            disabled={!canCreate}
          >
            <Plus className="h-4 w-4" />
            {t("create")}
          </Button>
        </div>

        <div className="flex flex-col gap-4">
          {workflows.map((workflow) => (
            <WorkflowCard
              key={workflow.uuid}
              workflow={workflow}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      </div>
      {dialogs}
    </>
  );
}
