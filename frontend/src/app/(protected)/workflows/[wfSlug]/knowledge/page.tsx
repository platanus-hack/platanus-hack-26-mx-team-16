"use client";

import { BookOpen, Upload } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Button } from "@/src/presentation/components/ui/button";
import { KnowledgeContent } from "@/src/presentation/workflows/workflow/knowledge-content";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowKnowledgePage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowConfig");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();
  const uploadRef = useRef<(() => void) | null>(null);

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
        { label: t("tabs.knowledge") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={BookOpen}
          title={t("tabs.knowledge")}
          subtitle={t("subtitle")}
          actions={
            <Button className="gap-2" onClick={() => uploadRef.current?.()}>
              <Upload className="h-4 w-4" />
              {t("actions.uploadDocument")}
            </Button>
          }
        />
        <div className="flex min-h-0 flex-1 flex-col">
          <KnowledgeContent wfSlug={wfSlug} onUploadRef={uploadRef} />
        </div>
      </PageContent>
    </WorkflowAppShell>
  );
}
