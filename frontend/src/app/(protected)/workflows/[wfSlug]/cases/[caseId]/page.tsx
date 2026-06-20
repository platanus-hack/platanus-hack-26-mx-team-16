"use client";

import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect } from "react";
import { caseNoun } from "@/src/application/lib/case-noun";
// Re-IA 2026-06: misma store que el sidebar (un solo fetch del workflow);
// la cases-store queda solo para la lista de casos del breadcrumb.
import { useWorkflowCasesStore } from "@/src/application/stores/workflow-cases-store";
import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { WorkflowCaseDetailView } from "../../../../../../presentation/workflows/cases/workflow-case-detail-view";
import { WorkflowAppShell } from "../../../../../../presentation/workflows/shared/workflow-app-shell";

export default function CaseDetailPage() {
  const tNav = useTranslations("Nav");
  const locale = useLocale();
  const params = useParams();
  const wfSlug = params.wfSlug as string;
  const caseId = params.caseId as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();
  const { cases, loadCases } = useWorkflowCasesStore();

  useEffect(() => {
    if (wfSlug) {
      loadWorkflow(wfSlug);
      loadCases(wfSlug);
    }
  }, [wfSlug, loadWorkflow, loadCases]);

  const workflowName = workflow?.name || tNav("workflows");
  const caseName = cases.find((c) => c.uuid === caseId)?.name || caseId;

  return (
    <WorkflowAppShell
      breadcrumbItems={[
        { label: tNav("workflows"), href: "/workflows" },
        { label: workflowName, href: `/workflows/${wfSlug}/cases` },
        {
          label: caseNoun(workflow, locale, 2),
          href: `/workflows/${wfSlug}/cases`,
        },
        { label: caseName },
      ]}
    >
      <WorkflowCaseDetailView workflowUuid={wfSlug} caseId={caseId} />
    </WorkflowAppShell>
  );
}
