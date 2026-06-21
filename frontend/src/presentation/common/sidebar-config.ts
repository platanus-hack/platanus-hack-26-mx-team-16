import type { LucideIcon } from "lucide-react";
import {
  KeyRound,
  LayoutDashboard,
  Settings,
  Settings2,
  Shield,
  Users,
} from "lucide-react";

export interface SidebarUser {
  name: string;
  email: string;
  avatar: string;
}

export interface SidebarTeam {
  name: string;
  logo: LucideIcon;
  plan: string;
}

export interface SidebarNavItem {
  i18nKey: string;
  url: string;
}

export interface SidebarNavMainItem extends SidebarNavItem {
  icon: LucideIcon;
  isActive?: boolean;
  disabled?: boolean;
  requiredPermission?: string;
  /** E5 · solo visible con `user.isStaff` (consola /staff, ADR 0001). */
  requiresStaff?: boolean;
  items?: SidebarNavItem[];
}

export interface SidebarProject {
  i18nKey: string;
  url: string;
  icon: LucideIcon;
  disabled?: boolean;
  requiredPermission?: string;
  /** E5 · solo visible con `user.isStaff` (consola /staff, ADR 0001). */
  requiresStaff?: boolean;
}

export interface SidebarConfig {
  user: SidebarUser;
  teams: SidebarTeam[];
  navMain: SidebarNavMainItem[];
  projects: SidebarProject[];
}

export const sidebarConfig: SidebarConfig = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/user.png",
  },
  teams: [
    {
      name: "Owliver",
      logo: Settings,
      plan: "Enterprise",
    },
  ],
  navMain: [
    {
      i18nKey: "dashboard",
      url: "/dashboard",
      icon: LayoutDashboard,
      requiredPermission: "dashboard.view",
    },
  ],
  projects: [
    {
      i18nKey: "apiKeys",
      url: "/api-keys",
      icon: KeyRound,
      requiredPermission: "tenant_settings.update",
    },
    {
      i18nKey: "roles",
      url: "/roles",
      icon: Shield,
      requiredPermission: "tenant_roles.view",
    },
    {
      i18nKey: "members",
      url: "/members",
      icon: Users,
      requiredPermission: "tenant_users.view",
    },
    {
      i18nKey: "settings",
      url: "/settings",
      icon: Settings2,
      requiredPermission: "tenant_settings.update",
    },
  ],
};
