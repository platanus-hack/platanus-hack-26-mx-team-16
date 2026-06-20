"use client";

import { CircleHelp } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { SuperuserActionsMenu } from "@/src/presentation/common/superuser-actions-menu";
import { ThemeSwitcher } from "@/src/presentation/common/theme-switcher";
import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/src/presentation/components/ui/breadcrumb";
import { Button } from "@/src/presentation/components/ui/button";
import { Separator } from "@/src/presentation/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/src/presentation/components/ui/sidebar";
import { WorkflowSidebar } from "./workflow-sidebar";

export interface BreadcrumbItemType {
  label: string;
  href?: string;
}

interface WorkflowAppShellProps {
  children: ReactNode;
  breadcrumbItems: BreadcrumbItemType[];
}

export function WorkflowAppShell({
  children,
  breadcrumbItems,
}: WorkflowAppShellProps) {
  const t = useTranslations("AppShell");

  return (
    <SidebarProvider>
      <WorkflowSidebar />
      <SidebarInset className="h-svh">
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
          <div className="flex min-w-0 flex-1 items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1 shrink-0" />
            <Separator
              orientation="vertical"
              className="mr-2 shrink-0 data-[orientation=vertical]:h-4"
            />
            <Breadcrumb className="min-w-0">
              <BreadcrumbList>
                {breadcrumbItems.map((item, index) => {
                  const isLast = index === breadcrumbItems.length - 1;
                  return (
                    <div key={index} className="contents">
                      <BreadcrumbItem
                        className={index > 0 ? "hidden md:block" : ""}
                      >
                        {isLast || !item.href ? (
                          <BreadcrumbPage>{item.label}</BreadcrumbPage>
                        ) : (
                          <BreadcrumbLink href={item.href}>
                            {item.label}
                          </BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                      {!isLast && (
                        <BreadcrumbSeparator className="hidden md:block" />
                      )}
                    </div>
                  );
                })}
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="flex shrink-0 items-center gap-2 px-4">
            <Button variant="ghost" size="lg">
              <CircleHelp className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">{t("help")}</span>
            </Button>
            <SuperuserActionsMenu />
            <LocaleSwitcher />
            <ThemeSwitcher />
          </div>
        </header>
        <div className="flex flex-1 min-h-0 flex-col">
          <div className="w-full flex-1 min-h-0 flex flex-col">{children}</div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
