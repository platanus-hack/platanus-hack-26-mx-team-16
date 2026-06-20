"use client";

import { FileOutput } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { SynthesisConfigView } from "@/src/presentation/workflows/run-summary/synthesis-config-view";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowSynthesisPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowConfig");
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
        { label: t("tabs.synthesis") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={FileOutput}
          title={t("tabs.synthesis")}
          subtitle={t("subtitle")}
        />
        <PageContent.Body>
          <SynthesisConfigView workflowId={wfSlug} />
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
