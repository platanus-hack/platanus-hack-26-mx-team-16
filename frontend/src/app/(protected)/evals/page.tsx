"use client";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { EvalsView } from "@/src/presentation/evals/evals-view";

export default function EvalsPage() {
  return (
    <PermissionGuard permission="workflows.view">
      <AppShell
        activePath="/evals"
        breadcrumbItems={[{ label: "Evaluaciones" }]}
      >
        <EvalsView />
      </AppShell>
    </PermissionGuard>
  );
}
