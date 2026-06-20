"use client";

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { WebhookSourceDetail } from "@/src/presentation/workflows/connections/webhook-source-detail";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

export default function WorkflowWebhookSourceDetailPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("Connections");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const sourceId = params.sourceId as string;
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
        {
          label: t("sources"),
          href: `/workflows/${wfSlug}/connections/sources`,
        },
        {
          label: t("webhookTitle"),
          href: `/workflows/${wfSlug}/connections/sources/webhooks`,
        },
        { label: "Origen webhook" },
      ]}
    >
      <WebhookSourceDetail workflowId={wfSlug} sourceId={sourceId} />
    </WorkflowAppShell>
  );
}
