"use client";

import {
  BookOpen,
  Briefcase,
  ChevronRight,
  FileOutput,
  Inbox,
  Layers,
  Send,
  Shield,
  ShieldCheck,
  Waypoints,
  Workflow as WorkflowIcon,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import type * as React from "react";
import { useEffect } from "react";
import { caseNoun } from "@/src/application/lib/case-noun";
import { useWorkflowDocumentsStore } from "@/src/application/stores/workflow-documents-store";
import { hasCapability } from "@/src/domain/entities/workflow";
import { NavUser } from "@/src/presentation/common/nav-user";
import { TenantHead } from "@/src/presentation/common/tenant-head";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/src/presentation/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
} from "@/src/presentation/components/ui/sidebar";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";

type NavItem = {
  route: string;
  label: string;
  icon: React.ComponentType;
};

function NavSkeletonRow() {
  return (
    <div className="flex items-center gap-2 px-2 py-1.5">
      <Skeleton className="h-4 w-4 rounded" />
      <Skeleton className="h-4 w-24 rounded" />
    </div>
  );
}

// Re-IA 2026-06 (brief workflow-detail-ia): el Caso es la única entidad
// operativa — los runs técnicos viven DENTRO del caso (tab Actividad), no como
// nav hermana. Tres grupos por intención; las tabs de feature siguen gateadas
// por capacidad del pipeline (E7 · F0).
export function WorkflowSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const params = useParams();
  const pathname = usePathname();
  const t = useTranslations("WorkflowNav");
  const locale = useLocale();
  const wfSlug = params.wfSlug as string;
  const { workflow, loadWorkflow } = useWorkflowDocumentsStore();

  useEffect(() => {
    if (wfSlug) {
      loadWorkflow(wfSlug);
    }
  }, [wfSlug, loadWorkflow]);

  const showAnalysisRules = hasCapability(workflow, "analysis");
  const showSynthesis = hasCapability(workflow, "structured_output");

  const isActiveRoute = (route: string) => {
    return pathname?.includes(`/workflows/${wfSlug}/${route}`);
  };

  const renderItem = ({ route, label, icon: Icon }: NavItem) => (
    <SidebarMenuItem key={route}>
      <SidebarMenuButton
        isActive={isActiveRoute(route)}
        tooltip={label}
        render={(buttonProps) => (
          <Link href={`/workflows/${wfSlug}/${route}`} {...buttonProps}>
            <Icon />
            <span>{label}</span>
          </Link>
        )}
      />
    </SidebarMenuItem>
  );

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TenantHead />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t("groups.operation")}</SidebarGroupLabel>
          <SidebarMenu>
            {renderItem({
              route: "cases",
              // Sustantivo del caso por workflow (plural); default «Casos».
              label: caseNoun(workflow, locale, 2),
              icon: Briefcase,
            })}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>{t("groups.configuration")}</SidebarGroupLabel>
          <SidebarMenu>
            {renderItem({
              route: "pipeline",
              label: t("items.pipeline"),
              icon: WorkflowIcon,
            })}
            {renderItem({
              route: "document-types",
              label: t("items.documentTypes"),
              icon: Layers,
            })}
            {renderItem({
              route: "knowledge",
              label: t("items.knowledge"),
              icon: BookOpen,
            })}
            {renderItem({
              route: "tools",
              label: t("items.tools"),
              icon: Wrench,
            })}
          </SidebarMenu>
        </SidebarGroup>

        {/* Solo si el pipeline tiene scope de caso: analyze ⇒ reglas,
            output+deliver ⇒ formato de salida (ambas fases son case-scope). */}
        {(!workflow || showAnalysisRules || showSynthesis) && (
          <SidebarGroup>
            <SidebarGroupLabel>{t("groups.cases")}</SidebarGroupLabel>
            <SidebarMenu>
              {/* Skeleton mientras carga para evitar pop-in. */}
              {!workflow ? (
                <>
                  <SidebarMenuItem>
                    <NavSkeletonRow />
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <NavSkeletonRow />
                  </SidebarMenuItem>
                </>
              ) : (
                <>
                  {showAnalysisRules &&
                    renderItem({
                      route: "analysis-rules",
                      label: t("items.analysisRules"),
                      icon: ShieldCheck,
                    })}
                  {showSynthesis &&
                    renderItem({
                      route: "synthesis",
                      label: t("items.synthesis"),
                      icon: FileOutput,
                    })}
                </>
              )}
            </SidebarMenu>
          </SidebarGroup>
        )}

        <SidebarGroup>
          <SidebarGroupLabel>{t("groups.administration")}</SidebarGroupLabel>
          <SidebarMenu>
            <SidebarMenuItem>
              <Collapsible
                defaultOpen={isActiveRoute("connections")}
                className="group/collapsible"
              >
                <CollapsibleTrigger
                  render={(props) => (
                    <SidebarMenuButton
                      {...props}
                      isActive={isActiveRoute("connections")}
                      tooltip={t("items.connections")}
                    >
                      <Waypoints />
                      <span>{t("items.connections")}</span>
                      <ChevronRight className="text-sidebar-foreground/50 ml-auto transition-transform duration-200 group-data-[open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  )}
                />
                <CollapsibleContent>
                  <SidebarMenuSub>
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton
                        isActive={isActiveRoute("connections/sources")}
                        render={(buttonProps) => (
                          <Link
                            href={`/workflows/${wfSlug}/connections/sources`}
                            {...buttonProps}
                          >
                            <Inbox />
                            <span>{t("items.sources")}</span>
                          </Link>
                        )}
                      />
                    </SidebarMenuSubItem>
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton
                        isActive={isActiveRoute("connections/destinations")}
                        render={(buttonProps) => (
                          <Link
                            href={`/workflows/${wfSlug}/connections/destinations`}
                            {...buttonProps}
                          >
                            <Send />
                            <span>{t("items.destinations")}</span>
                          </Link>
                        )}
                      />
                    </SidebarMenuSubItem>
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>
            </SidebarMenuItem>
            {renderItem({
              route: "permissions",
              label: t("items.permissions"),
              icon: Shield,
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
