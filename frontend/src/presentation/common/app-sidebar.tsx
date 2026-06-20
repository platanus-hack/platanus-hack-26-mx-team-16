"use client";

import type * as React from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import { usePermissions } from "@/src/application/hooks/use-permissions";
import { NavMain } from "@/src/presentation/common/nav-main";
import { NavProjects } from "@/src/presentation/common/nav-projects";
import { NavUser } from "@/src/presentation/common/nav-user";
import { sidebarConfig } from "@/src/presentation/common/sidebar-config";
import { TenantHead } from "@/src/presentation/common/tenant-head";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/src/presentation/components/ui/sidebar";

export function AppSidebar({
  activePath,
  ...props
}: React.ComponentProps<typeof Sidebar> & { activePath?: string }) {
  const { hasPermission } = usePermissions();
  // E5 · entradas staff: se OCULTAN (no se deshabilitan) para no-staff.
  const isStaff = useSessionStore((s) => s.user?.isStaff === true);

  const navMainItems = sidebarConfig.navMain
    .filter((item) => !item.requiresStaff || isStaff)
    .map((item) => ({
      ...item,
      disabled:
        item.disabled ||
        (item.requiredPermission
          ? !hasPermission(item.requiredPermission)
          : false),
    }));

  const projectItems = sidebarConfig.projects
    .filter((item) => !item.requiresStaff || isStaff)
    .map((item) => ({
      ...item,
      disabled:
        item.disabled ||
        (item.requiredPermission
          ? !hasPermission(item.requiredPermission)
          : false),
    }));

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TenantHead />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navMainItems} activePath={activePath} />
        <NavProjects projects={projectItems} activePath={activePath} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
