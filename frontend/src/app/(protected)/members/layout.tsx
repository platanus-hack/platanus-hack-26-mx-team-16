import type { Metadata } from "next";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";

export const metadata: Metadata = {
  title: "Miembros",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <PermissionGuard permission="tenant_users.view">{children}</PermissionGuard>
  );
}
