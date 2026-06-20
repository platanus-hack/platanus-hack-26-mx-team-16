"use client";

import { Inbox } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { SourceTypeGrid } from "@/src/presentation/workflows/connections/source-type-grid";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

export default function WorkflowSourcesPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("Connections");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();

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
        { label: t("title") },
        { label: t("sources") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={Inbox}
          title={t("sourcesTitle")}
          subtitle={t("subtitle")}
        />
        <PageContent.Body>
          <div className="w-full">
            <SourceTypeGrid
              workflowSlug={wfSlug}
              workflowUuid={workflow?.uuid ?? null}
            />
          </div>
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
