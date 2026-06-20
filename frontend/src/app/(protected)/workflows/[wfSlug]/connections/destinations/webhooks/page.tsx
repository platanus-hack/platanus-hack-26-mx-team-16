"use client";

import { Plus, Webhook } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Button } from "@/src/presentation/components/ui/button";
import { WebhookDestinationsList } from "@/src/presentation/workflows/connections/webhook-destinations-list";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

export default function WorkflowWebhookDestinationsPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("Connections");
  const tw = useTranslations("WebhookDestinations");
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();
  const addRef = useRef<(() => void) | null>(null);

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
        { label: tw("title") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title={tw("title")}
          subtitle={t("subtitle")}
          showBack
          onBack={() =>
            router.push(`/workflows/${wfSlug}/connections/destinations`)
          }
          actions={
            <Button className="gap-2" onClick={() => addRef.current?.()}>
              <Plus className="h-4 w-4" />
              {tw("addDestination")}
            </Button>
          }
        />
        <PageContent.Body>
          <div className="flex min-h-0 flex-1 flex-col">
            <WebhookDestinationsList workflowId={wfSlug} onAddRef={addRef} />
          </div>
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
