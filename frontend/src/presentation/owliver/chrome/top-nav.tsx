/**
 * TopNav — public Owliver header (§F3): brand, compact navigation, account entry
 * and the primary audit action. Server-component friendly.
 */

import { LogIn, Radar } from "lucide-react";
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";

export type TopNavProps = {
  /** Render the Watchlist link (e.g. when a session exists). */
  showWatchlist?: boolean;
  className?: string;
};

const NAV_LINKS = [{ href: "/watch", label: "Hall of Shame" }];

const navLinkClass =
  "rounded-full px-3.5 py-2 text-sm font-medium text-on-surface-variant outline-none transition-colors hover:bg-background hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring";

export function TopNav({ showWatchlist = false, className }: TopNavProps) {
  return (
    <header
      data-slot="top-nav"
      className={cn(
        "sticky top-0 z-40 w-full border-b border-outline-variant/80 bg-background/92 backdrop-blur-md",
        className
      )}
    >
      <div className="mx-auto flex h-[80px] max-w-6xl items-center justify-between gap-3 px-4 md:px-6">
        <div className="flex min-w-0 items-center gap-5">
          <BrandLockup size="md" />
          <nav
            className="hidden items-center gap-1 rounded-full bg-surface-container-low px-1.5 py-1 md:flex"
            aria-label="Principal"
          >
            {NAV_LINKS.map((l) => (
              <Link key={l.href} href={l.href} className={navLinkClass}>
                {l.label}
              </Link>
            ))}
            {showWatchlist && (
              <>
                <Link href="/watchlist" className={navLinkClass}>
                  Watchlist
                </Link>
                <Link href="/onboarding" className={navLinkClass}>
                  Primeros pasos
                </Link>
              </>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            aria-label="Entrar a cuenta"
            className={cn(
              buttonVariants({ variant: "outline", size: "icon" }),
              "sm:hidden"
            )}
          >
            <LogIn className="size-4" />
          </Link>
          <Link
            href="/login"
            className={cn(
              buttonVariants({ variant: "outline", size: "default" }),
              "hidden sm:inline-flex"
            )}
          >
            <LogIn className="size-4" />
            Entrar
          </Link>
          <Link
            href="/scan"
            className={buttonVariants({ variant: "default", size: "default" })}
          >
            <Radar className="size-4" />
            Auditar URL
          </Link>
        </div>
      </div>
    </header>
  );
}
