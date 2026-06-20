"use client";

import { PermissionGuard } from "@/src/presentation/common/permission-guard";

export default function WorkflowDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PermissionGuard permission="workflows.view">{children}</PermissionGuard>
  );
}
