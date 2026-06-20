"use client";

import { Plus, Wrench } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef } from "react";

import { useWorkflowQuery } from "@/src/application/hooks/queries/workflows";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";
import { ToolsView } from "@/src/presentation/workflows/tools/tools-view";

export default function WorkflowToolsPage() {
  const tNav = useTranslations("Nav");
  const tWfNav = useTranslations("WorkflowNav");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const createRef = useRef<(() => void) | null>(null);

  const { data: workflow } = useWorkflowQuery(wfSlug);
  const workflowName = workflow?.name || tNav("workflows");

  return (
    <WorkflowAppShell
      breadcrumbItems={[
        { label: tNav("workflows"), href: "/workflows" },
        { label: workflowName, href: `/workflows/${wfSlug}/cases` },
        { label: tWfNav("items.tools") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={Wrench}
          title="Herramientas"
          subtitle="Servicios externos que este workflow puede invocar"
          actions={
            <ActionButton icon={<Plus />} onClick={() => createRef.current?.()}>
              Nueva herramienta
            </ActionButton>
          }
        />
        <PageContent.Body>
          <ToolsView workflowId={wfSlug} onCreateRef={createRef} />
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
