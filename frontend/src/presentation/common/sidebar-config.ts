import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  ClipboardCheck,
  CreditCard,
  Database,
  FolderOpen,
  KeyRound,
  LayoutDashboard,
  Settings,
  Settings2,
  Shield,
  TrendingUp,
  Users,
  Waypoints,
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
      name: "LlamitAI",
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
    {
      i18nKey: "workflows",
      url: "/workflows",
      icon: FolderOpen,
      requiredPermission: "workflows.view",
    },
    {
      i18nKey: "review",
      url: "/review",
      icon: ClipboardCheck,
      requiredPermission: "workflows.view",
    },
    {
      i18nKey: "knowledge",
      url: "/knowledge",
      icon: BookOpen,
      disabled: true,
    },
    {
      i18nKey: "dataSources",
      url: "/data-sources",
      icon: Database,
      disabled: true,
    },
  ],
  projects: [
    {
      i18nKey: "integrations",
      url: "/integrations",
      icon: Waypoints,
    },
    // /evals y /staff ocultos del nav 2026-06-12 (rutas siguen vivas por URL)
    // hasta tener plan de mejora; restaurar las entradas al retomarlos.
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
      i18nKey: "usage",
      url: "/usage",
      icon: TrendingUp,
      requiredPermission: "workflows.view_usage",
    },
    {
      i18nKey: "billing",
      url: "/billing",
      icon: CreditCard,
      disabled: true,
    },
    {
      i18nKey: "settings",
      url: "/settings",
      icon: Settings2,
      requiredPermission: "tenant_settings.update",
    },
  ],
};
