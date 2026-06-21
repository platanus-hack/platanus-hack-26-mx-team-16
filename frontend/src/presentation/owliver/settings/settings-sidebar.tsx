/**
 * SettingsSidebar — the secondary nav for Owliver's account/settings cluster
 * (design `e3EBfA`). A hairline-ringed card with pill nav items: active item is a
 * `primary-container` pill (violet-aligned) with a `primary` icon; idle items are quiet
 * (`muted-foreground` text + `outline` icon) and tint on hover. Pure presentation;
 * the caller passes `activePath` so this stays a server component.
 */

import {
  Bell,
  Building2,
  KeyRound,
  LayoutDashboard,
  type LucideIcon,
  ShieldCheck,
  User,
  Users,
} from "lucide-react";
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";

type SettingsNavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { href: "/dashboard", label: "Panel", icon: LayoutDashboard },
  { href: "/profile", label: "Perfil", icon: User },
  { href: "/members", label: "Equipo", icon: Users },
  { href: "/roles", label: "Roles", icon: ShieldCheck },
  { href: "/settings", label: "Organización", icon: Building2 },
  { href: "/api-keys", label: "API", icon: KeyRound },
  { href: "/settings/notifications", label: "Notificaciones", icon: Bell },
];

export type SettingsSidebarProps = {
  /** Pathname of the active settings page (e.g. "/profile"). */
  activePath: string;
  className?: string;
};

export function SettingsSidebar({
  activePath,
  className,
}: SettingsSidebarProps) {
  return (
    <nav
      data-slot="settings-sidebar"
      aria-label="Ajustes"
      className={cn(
        "flex w-full shrink-0 flex-col gap-1.5 rounded-2xl border border-outline-variant bg-card px-4 pt-5 pb-6 md:w-[284px]",
        className
      )}
    >
      <p className="px-3 pb-3 text-xs font-semibold uppercase tracking-wider text-outline">
        Ajustes
      </p>
      {SETTINGS_NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = activePath === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-full px-4 py-2.5 text-[15px] transition-colors",
              active
                ? "bg-primary-container font-semibold text-on-primary-container"
                : "font-medium text-muted-foreground hover:bg-surface-container hover:text-foreground"
            )}
          >
            <Icon
              aria-hidden
              className={cn(
                "size-[19px] shrink-0",
                active ? "text-primary" : "text-outline"
              )}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
