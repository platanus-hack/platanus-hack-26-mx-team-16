"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import { cn } from "@/src/application/lib/utils";
import { Badge } from "@/src/presentation/components/ui/badge";
import { buttonVariants } from "@/src/presentation/components/ui/button";

/**
 * E5 · shell propio de la consola staff (ADR 0001).
 *
 * SIN selector de tenant a propósito: la cola es cross-tenant y cada fila
 * lleva su tenant como badge. Header near-flat (hairline + bg-background),
 * nav mínima: Cola L1 y, solo para `staff_admin`, Auditoría.
 */
export function StaffShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const user = useSessionStore((s) => s.user);
  const isAdmin = user?.staffRole === "staff_admin";

  const navItems = [
    { label: "Colas", href: "/staff" },
    ...(isAdmin
      ? [
          { label: "Métricas QA", href: "/staff/metrics" },
          { label: "Auditoría", href: "/staff/audit" },
        ]
      : []),
  ];

  const displayName =
    [user?.firstName, user?.lastName].filter(Boolean).join(" ") ||
    user?.username ||
    "";

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-10 border-b bg-background">
        <div className="flex h-14 items-center gap-4 px-6">
          <Link href="/staff" className="flex items-center gap-2.5">
            <span className="text-sm font-semibold tracking-tight">
              Doxiq
            </span>
            <Badge variant="secondary" className="font-normal">
              Consola interna
            </Badge>
          </Link>
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const active =
                item.href === "/staff"
                  ? pathname === "/staff" || pathname.startsWith("/staff/tasks")
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-md px-2.5 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {displayName && (
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {displayName}
              </span>
            )}
            <Link
              href="/dashboard"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              <ArrowLeft className="size-4" />
              Volver al panel
            </Link>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        {children}
      </main>
    </div>
  );
}
