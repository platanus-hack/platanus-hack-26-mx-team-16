"use client";

import { Download, Plus, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Button } from "@/src/presentation/components/ui/button";
import { AnalysisRulesContent } from "@/src/presentation/workflows/workflow/analysis-rules-content";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowAnalysisRulesPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowConfig");
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();

  const createRef = useRef<(() => void) | null>(null);
  const importRef = useRef<(() => void) | null>(null);
  const exportRef = useRef<(() => void) | null>(null);

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
        { label: t("tabs.analysisRules") },
      ]}
    >
      <PageContent>
        <PageContent.Header
          icon={ShieldCheck}
          title={t("tabs.analysisRules")}
          subtitle={t("subtitle")}
          actions={
            <>
              <Button className="gap-2" onClick={() => createRef.current?.()}>
                <Plus className="h-4 w-4" />
                {t("actions.addRule")}
              </Button>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => importRef.current?.()}
              >
                <Upload className="h-4 w-4" />
                {t("actions.import")}
              </Button>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => exportRef.current?.()}
              >
                <Download className="h-4 w-4" />
                {t("actions.export")}
              </Button>
              <Button variant="outline" className="gap-2" onClick={() => {}}>
                <Sparkles className="h-4 w-4" />
                {t("actions.suggestRules")}
              </Button>
            </>
          }
        />
        <PageContent.Body>
          <AnalysisRulesContent
            workflowId={wfSlug}
            onCreateRef={createRef}
            onImportRef={importRef}
            onExportRef={exportRef}
          />
        </PageContent.Body>
      </PageContent>
    </WorkflowAppShell>
  );
}
