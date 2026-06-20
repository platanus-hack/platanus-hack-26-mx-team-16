import type { Metadata } from "next";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import { DoctypeOperationsWidget } from "@/src/presentation/components/common/doctype-operations-widget";

export const metadata: Metadata = {
  title: "Workflows",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <PermissionGuard permission="workflows.view">
      {children}
      <DoctypeOperationsWidget />
    </PermissionGuard>
  );
}
