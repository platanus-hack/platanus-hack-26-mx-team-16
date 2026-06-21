"use client";

import { Crown } from "lucide-react";
import { useSessionStore } from "@/src/application/contexts/session-store";
import { useOnboardTenantWizardStore } from "@/src/application/stores/onboard-tenant-wizard-store";
import { detectBrowserTimezone } from "@/src/domain/catalogs/timezones";
import { Button } from "@/src/presentation/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";
import { OnboardTenantWizard } from "@/src/presentation/superuser/onboard-tenant/onboard-tenant-wizard";

/**
 * Header-level dropdown that exposes superuser-only actions. Renders
 * nothing when the current session user is not a superuser. New
 * actions plug into the menu by adding more `DropdownMenuItem`s below
 * the first entry.
 */
export function SuperuserActionsMenu() {
  const isSuperuser = useSessionStore((s) => s.user?.isSuperuser === true);
  const openOnboardWizard = useOnboardTenantWizardStore((s) => s.openWizard);

  if (!isSuperuser) return null;

  const handleRegisterTenant = () => {
    openOnboardWizard({
      countryCode: "MX",
      currencyCode: "MXN",
      timeZone: detectBrowserTimezone(),
    });
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-lg"
              aria-label="Acciones de superusuario"
            >
              <Crown className="h-[1.2rem] w-[1.2rem] text-tertiary" />
            </Button>
          }
        />
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              Superusuario
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleRegisterTenant}>
              Registrar Tenant
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <OnboardTenantWizard />
    </>
  );
}
