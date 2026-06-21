import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";

interface AuthContainerProps {
  icon: LucideIcon;
  title: string;
  description: string;
  children: ReactNode;
}

/**
 * Shared shell for the auth forms (register, reset-password, …). Mirrors the
 * Owliver login page: a single centered card led by the brand lockup (owl +
 * wordmark), with the per-page lucide icon as a small accent above the title —
 * one visual language across every auth surface.
 */
export function AuthContainer({
  icon: Icon,
  title,
  description,
  children,
}: AuthContainerProps) {
  return (
    <div className="relative grid min-h-screen place-items-center bg-background px-4 py-12">
      <div className="absolute top-4 right-4 z-10">
        <LocaleSwitcher />
      </div>

      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-8 rounded-3xl border border-border bg-card p-8 shadow-sm sm:p-10">
          <BrandLockup href="/" size="lg" owlState="idle" />

          <div className="flex flex-col items-center gap-3 text-center">
            <div className="flex size-11 items-center justify-center rounded-full bg-primary/10">
              <Icon className="size-5 text-primary" aria-hidden />
            </div>
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                {title}
              </h1>
              <p className="text-sm text-pretty text-muted-foreground">
                {description}
              </p>
            </div>
          </div>

          <div className="w-full">{children}</div>
        </div>
      </div>
    </div>
  );
}
