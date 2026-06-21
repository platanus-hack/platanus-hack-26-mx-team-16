"use client";

/**
 * AccountMenu — the "Mi Cuenta" entry in the public TopNav when a session
 * exists. Replaces the plain `/dashboard` link with a dropdown that surfaces
 * the dashboard shortcut and a "Cerrar sesión" action (mirrors the logout flow
 * in `NavUser`: POST /api/auth/logout → clear the client store → home).
 */

import { LayoutDashboard, LogOut, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  useSession,
  useSessionActions,
} from "@/src/application/contexts/session";
import { cn } from "@/src/application/lib/utils";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";

function getDisplayName(
  firstName?: string | null,
  lastName?: string | null,
  username?: string
): string {
  if (firstName || lastName)
    return [firstName, lastName].filter(Boolean).join(" ");
  return username ?? "";
}

export function AccountMenu() {
  const router = useRouter();
  const { user } = useSession();
  const { clearSession } = useSessionActions();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const displayName = getDisplayName(
    user?.firstName,
    user?.lastName,
    user?.username
  );
  const email = user?.emailAddress?.email ?? "";

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      clearSession();
      router.push("/");
      router.refresh();
    } catch (error) {
      console.error("Error al cerrar sesión:", error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Mi Cuenta"
        className={cn(
          buttonVariants({ variant: "outline", size: "default" }),
          "px-2.5 sm:px-4"
        )}
      >
        <UserRound className="size-4" />
        <span className="hidden sm:inline">Mi Cuenta</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={6} className="min-w-56">
        {(displayName || email) && (
          <>
            <DropdownMenuLabel className="font-normal">
              <div className="grid gap-0.5">
                {displayName && (
                  <span className="truncate text-sm font-medium text-foreground">
                    {displayName}
                  </span>
                )}
                {email && <span className="truncate text-xs">{email}</span>}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem onClick={() => router.push("/dashboard")}>
          <LayoutDashboard />
          Dashboard
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          onClick={handleLogout}
          disabled={isLoggingOut}
        >
          <LogOut />
          {isLoggingOut ? "Cerrando sesión…" : "Cerrar sesión"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
