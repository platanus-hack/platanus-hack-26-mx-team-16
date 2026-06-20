"use client";

import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect } from "react";

import { caseNoun } from "@/src/application/lib/case-noun";
// Re-IA 2026-06: misma store que el sidebar ⇒ un solo fetch del workflow por
// superficie (antes: cases-store aquí + documents-store en el sidebar).
import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { CasesView } from "@/src/presentation/workflows/cases/cases-view";
import { WorkflowAppShell } from "../../../../../presentation/workflows/shared/workflow-app-shell";

export default function WorkflowCasesPage() {
  const tNav = useTranslations("Nav");
  const locale = useLocale();
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
        { label: workflowName, href: `/workflows/${wfSlug}/cases` },
        { label: caseNoun(workflow, locale, 2) },
      ]}
    >
      <CasesView />
    </WorkflowAppShell>
  );
}
