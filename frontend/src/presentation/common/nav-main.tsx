"use client";

import { ChevronRight, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/src/presentation/components/ui/collapsible";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/src/presentation/components/ui/sidebar";

export function NavMain({
  items,
  activePath,
}: {
  items: {
    i18nKey: string;
    url: string;
    icon?: LucideIcon;
    isActive?: boolean;
    disabled?: boolean;
    items?: {
      i18nKey: string;
      url: string;
    }[];
  }[];
  activePath?: string;
}) {
  const t = useTranslations("Nav");

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{t("platform")}</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => {
          const isItemActive =
            activePath === item.url ||
            item.items?.some((subItem) => subItem.url === activePath);
          const isActive = item.isActive || isItemActive;
          const label = t(item.i18nKey);

          if (!item.items || item.items.length === 0) {
            return (
              <SidebarMenuItem key={item.i18nKey}>
                {item.disabled ? (
                  <SidebarMenuButton
                    disabled
                    className="opacity-50 cursor-not-allowed"
                  >
                    {item.icon && <item.icon />}
                    <span>{label}</span>
                  </SidebarMenuButton>
                ) : (
                  <SidebarMenuButton
                    isActive={isItemActive}
                    tooltip={label}
                    render={(props) => (
                      <Link href={item.url} {...props}>
                        {item.icon && <item.icon />}
                        <span>{label}</span>
                      </Link>
                    )}
                  />
                )}
              </SidebarMenuItem>
            );
          }

          return (
            <SidebarMenuItem key={item.i18nKey}>
              <Collapsible defaultOpen={isActive} className="group/collapsible">
                <CollapsibleTrigger
                  render={(props) => (
                    <SidebarMenuButton {...props} isActive={isItemActive}>
                      {item.icon && <item.icon />}
                      <span>{label}</span>
                      <ChevronRight className="text-sidebar-foreground/50 ml-auto transition-transform duration-200 group-data-[open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  )}
                />
                <CollapsibleContent>
                  <SidebarMenuSub>
                    {item.items.map((subItem) => (
                      <SidebarMenuSubItem key={subItem.i18nKey}>
                        <SidebarMenuSubButton
                          isActive={activePath === subItem.url}
                          render={(props) => (
                            <Link href={subItem.url} {...props}>
                              <span>{t(subItem.i18nKey)}</span>
                            </Link>
                          )}
                        />
                      </SidebarMenuSubItem>
                    ))}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>
            </SidebarMenuItem>
          );
        })}
      </SidebarMenu>
    </SidebarGroup>
  );
}
