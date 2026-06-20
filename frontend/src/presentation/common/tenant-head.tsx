"use client";

import { Building2, ChevronsUpDown } from "lucide-react";
import { useCallback } from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import {
  useTenantStore,
  useTenants,
  useTenantsLoading,
} from "@/src/application/stores/tenant-store";
import type { Tenant } from "@/src/domain/entities/tenant";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/src/presentation/components/ui/sidebar";

function TenantLogo({ tenant }: { tenant: Tenant }) {
  return (
    <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center overflow-hidden rounded-lg">
      {tenant.logoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={tenant.logoUrl}
          alt={tenant.name}
          className="size-full object-cover"
        />
      ) : (
        <Building2 className="size-4" />
      )}
    </div>
  );
}

// URL prefixes whose second segment is a tenant-scoped resource id/slug.
// After switching tenants those ids no longer resolve, so we land the user
// on the index page instead of a guaranteed-stale detail URL.
const TENANT_SCOPED_PREFIXES = ["/workflows/"];

function resolveTargetPath(pathname: string): string {
  for (const prefix of TENANT_SCOPED_PREFIXES) {
    if (pathname.startsWith(prefix)) return prefix.replace(/\/$/, "");
  }
  return pathname;
}

export function TenantHead() {
  const tenant = useSessionStore((s) => s.tenant);
  const tenants = useTenants();
  const loading = useTenantsLoading();
  const selectTenant = useTenantStore((s) => s.selectTenant);
  const { isMobile } = useSidebar();

  const hasMultipleTenants = tenants.length > 1;

  const handleTenantChange = useCallback(
    (option: Tenant) => {
      if (option.uuid === tenant?.uuid) return;
      selectTenant(option).then(() => {
        // Hard reload to nuke React Query caches, in-flight requests, and
        // zustand stores hydrated from the previous tenant. router.refresh()
        // alone re-runs Server Components but leaves client caches stale.
        // Read pathname on demand so this component doesn't subscribe to
        // every route change (rerender-defer-reads).
        if (typeof window === "undefined") return;
        window.location.assign(resolveTargetPath(window.location.pathname));
      });
    },
    [selectTenant, tenant?.uuid]
  );

  if (!tenant) return null;

  const subtitleParts = [tenant.countryCode].filter(Boolean);

  const summary = (
    <>
      <TenantLogo tenant={tenant} />
      <div className="grid flex-1 text-left text-sm leading-tight">
        <span className="truncate font-medium">{tenant.name}</span>
        <span className="text-muted-foreground truncate text-xs">
          {subtitleParts.join(" / ")}
        </span>
      </div>
      {hasMultipleTenants && <ChevronsUpDown className="ml-auto size-4" />}
    </>
  );

  if (!hasMultipleTenants) {
    return (
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" className="gap-2">
            {summary}
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    );
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <SidebarMenuButton
            size="lg"
            className="cursor-pointer data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            render={(props) => (
              <DropdownMenuTrigger {...props}>{summary}</DropdownMenuTrigger>
            )}
          />
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-64 rounded-lg"
            align="start"
            side={isMobile ? "bottom" : "right"}
            sideOffset={4}
          >
            <DropdownMenuGroup>
              <DropdownMenuLabel className="text-muted-foreground text-xs">
                Cambiar Tenant
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {loading ? (
                <DropdownMenuItem disabled>
                  Cargando tenants...
                </DropdownMenuItem>
              ) : (
                tenants.map((option) => (
                  <DropdownMenuItem
                    key={option.uuid}
                    onClick={() => handleTenantChange(option)}
                    className="flex cursor-pointer items-center gap-3 p-3"
                  >
                    <Building2 className="text-muted-foreground h-4 w-4" />
                    <div className="flex flex-1 flex-col gap-0.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{option.name}</span>
                        {tenant.uuid === option.uuid && (
                          <Badge variant="default" className="text-xs">
                            Actual
                          </Badge>
                        )}
                      </div>
                      <div className="text-muted-foreground flex items-center gap-1 text-xs">
                        <span>{option.countryCode || option.slug}</span>
                      </div>
                    </div>
                  </DropdownMenuItem>
                ))
              )}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
