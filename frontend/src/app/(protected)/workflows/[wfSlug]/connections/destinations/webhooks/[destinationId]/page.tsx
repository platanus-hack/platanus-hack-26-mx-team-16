"use client";

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWebhookDestinationQuery } from "@/src/application/hooks/queries/webhook-destinations";
import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { WebhookDestinationDetail } from "@/src/presentation/workflows/connections/webhook-destination-detail";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

export default function WorkflowWebhookDestinationDetailPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("Connections");
  const tw = useTranslations("WebhookDestinations");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const destinationId = params.destinationId as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();
  const { data: destination } = useWebhookDestinationQuery(
    wfSlug,
    destinationId
  );

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
          label: t("destinations"),
          href: `/workflows/${wfSlug}/connections/destinations`,
        },
        {
          label: tw("title"),
          href: `/workflows/${wfSlug}/connections/destinations/webhooks`,
        },
        { label: destination?.name ?? "…" },
      ]}
    >
      <WebhookDestinationDetail
        workflowId={wfSlug}
        destinationId={destinationId}
      />
    </WorkflowAppShell>
  );
}
