"use client";

import { Plus, Webhook } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Button } from "@/src/presentation/components/ui/button";
import { WebhookSourcesList } from "@/src/presentation/workflows/connections/webhook-sources-list";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

export default function WorkflowWebhookSourcesPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("Connections");
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
          label: t("sources"),
          href: `/workflows/${wfSlug}/connections/sources`,
        },
        { label: t("webhookTitle") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title={t("webhookTitle")}
          subtitle={t("subtitle")}
          showBack
          onBack={() => router.push(`/workflows/${wfSlug}/connections/sources`)}
          actions={
            <Button className="gap-2" onClick={() => addRef.current?.()}>
              <Plus className="h-4 w-4" />
              Nueva
            </Button>
          }
        />
        <PageContent.Body>
          <div className="flex min-h-0 flex-1 flex-col">
            <WebhookSourcesList
              workflowId={workflow?.uuid ?? null}
              onAddRef={addRef}
            />
          </div>
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
