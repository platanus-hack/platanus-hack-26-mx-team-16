"use client";

import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/src/presentation/components/ui/sidebar";

export function NavProjects({
  projects,
  activePath,
}: {
  projects: {
    i18nKey: string;
    url: string;
    icon: LucideIcon;
    disabled?: boolean;
  }[];
  activePath?: string;
}) {
  const t = useTranslations("Nav");

  return (
    <SidebarGroup className="group-data-[collapsible=icon]:hidden">
      <SidebarGroupLabel>{t("team")}</SidebarGroupLabel>
      <SidebarMenu>
        {projects.map((item) => {
          const label = t(item.i18nKey);
          return (
            <SidebarMenuItem key={item.i18nKey}>
              {item.disabled ? (
                <SidebarMenuButton
                  disabled
                  className="opacity-50 cursor-not-allowed"
                >
                  <item.icon />
                  <span>{label}</span>
                </SidebarMenuButton>
              ) : (
                <SidebarMenuButton
                  isActive={activePath === item.url}
                  render={(props) => (
                    <Link href={item.url} {...props}>
                      <item.icon />
                      <span>{label}</span>
                    </Link>
                  )}
                />
              )}
            </SidebarMenuItem>
          );
        })}
      </SidebarMenu>
    </SidebarGroup>
  );
}
