"use client";

import { FilePlus, Layers } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { httpDocumentTypeRepository } from "@/src/infrastructure/repositories/http-doctype";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Button } from "@/src/presentation/components/ui/button";
import { ImportDoctypeButton } from "@/src/presentation/workflows/document-types/detail/import-doctype-button";
import { WorkflowDocumentTypesView } from "@/src/presentation/workflows/document-types/workflow-doctypes-view";
import { WorkflowBundleActions } from "@/src/presentation/workflows/workflow/workflow-bundle-actions";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowDocumentTypesPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowConfig");
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();

  useEffect(() => {
    if (wfSlug) {
      loadWorkflow(wfSlug);
    }
  }, [wfSlug, loadWorkflow]);

  const workflowName = workflow?.name || tNav("workflows");

  const handleAddDocumentType = async () => {
    const response = await httpDocumentTypeRepository.create(
      { name: "Untitled" },
      wfSlug
    );
    if ("data" in response) {
      router.push(`/workflows/${wfSlug}/document-types/${response.data.uuid}`);
    }
  };

  return (
    <WorkflowAppShell
      breadcrumbItems={[
        { label: tNav("workflows"), href: "/workflows" },
        { label: workflowName },
        { label: t("tabs.documentTypes") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={Layers}
          title={t("tabs.documentTypes")}
          subtitle={t("subtitle")}
          actions={
            <>
              <Button className="gap-2" onClick={handleAddDocumentType}>
                <FilePlus className="h-4 w-4" />
                {t("actions.addDocumentType")}
              </Button>
              <ImportDoctypeButton />
              <WorkflowBundleActions workflowId={wfSlug} />
            </>
          }
        />
        <PageContent.Body scroll={false}>
          <WorkflowDocumentTypesView />
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
