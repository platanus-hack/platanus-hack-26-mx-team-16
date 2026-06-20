"use client";

import { Workflow as WorkflowIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWorkflowPipelineQuery } from "@/src/application/hooks/queries/pipelines";
import { usePermissions } from "@/src/application/hooks/use-permissions";
import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { PipelineEditor } from "@/src/presentation/pipelines/pipeline-editor";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowPipelinePage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowConfig");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();
  const { hasPermission } = usePermissions();
  // El gate autoritativo lo aplica el backend (require_workflow_action("manage")).
  // Aquí solo decidimos si mostrar los controles de edición/publicación.
  const canManage = hasPermission("workflows.update");
  // Nombre + versión del pipeline para el subtítulo del header (react-query
  // dedupe: el editor consulta la misma key, así que no hay fetch extra).
  const { data: pipeline } = useWorkflowPipelineQuery(wfSlug);

  useEffect(() => {
    if (wfSlug) {
      loadWorkflow(wfSlug);
    }
  }, [wfSlug, loadWorkflow]);

  const workflowName = workflow?.name || tNav("workflows");

  return (
    <WorkflowAppShell
      breadcrumbItems={[
        { label: tNav("workflows"), href: "/workflows" },
        { label: workflowName },
        { label: t("tabs.pipeline") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={WorkflowIcon}
          title={t("tabs.pipeline")}
          subtitle={
            pipeline
              ? `${pipeline.name} · v${pipeline.currentVersion}`
              : t("subtitle")
          }
        />
        <PageContent.Body scroll={false}>
          <PipelineEditor workflowId={wfSlug} canManage={canManage} />
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
