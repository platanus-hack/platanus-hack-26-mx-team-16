/**
 * TopNav — the public Owliver header (§F3): BrandLockup + nav links + the amber
 * "Escanear mi sitio" CTA (tertiary = owl-eyes). NO sidebar — this serves both
 * the anonymous viral audience and the signed-in watchlist user from one bar.
 *
 * Server-component friendly (the nav links are plain anchors). The CTA is a
 * `tertiary` Button styled as a link. Sticky, hairline-bottom, theme-aware so it
 * survives the light shell (it never renders inside the SOC theater).
 */
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";

export type TopNavProps = {
  /** Render the Watchlist link (e.g. when a session exists). */
  showWatchlist?: boolean;
  className?: string;
};

const NAV_LINKS = [
  { href: "/", label: "Leaderboard" },
  { href: "/scan", label: "Escanear" },
];

export function TopNav({ showWatchlist = false, className }: TopNavProps) {
  return (
    <header
      data-slot="top-nav"
      className={cn(
        "sticky top-0 z-40 w-full border-b border-outline-variant bg-background/85 backdrop-blur-md",
        className
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-6">
        <div className="flex items-center gap-6">
          <BrandLockup size="md" />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Principal">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-full px-3 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container hover:text-foreground"
              >
                {l.label}
              </Link>
            ))}
            {showWatchlist && (
              <Link
                href="/watchlist"
                className="rounded-full px-3 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container hover:text-foreground"
              >
                Watchlist
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/scan"
            className={buttonVariants({ variant: "tertiary", size: "default" })}
          >
            Escanear mi sitio
          </Link>
        </div>
      </div>
    </header>
  );
}
