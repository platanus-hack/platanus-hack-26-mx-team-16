"use client";

import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { ReviewQueueView } from "@/src/presentation/review/review-queue-view";

export default function ReviewPage() {
  return (
    <PermissionGuard permission="workflows.view">
      <AppShell activePath="/review" breadcrumbItems={[{ label: "Revisión" }]}>
        <ReviewQueueView />
      </AppShell>
    </PermissionGuard>
  );
}
