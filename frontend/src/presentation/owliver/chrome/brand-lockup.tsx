/**
 * BrandLockup — Owliver's wordmark: the owl mark (reusing `OwlMascot`) + the
 * "Owliver" name + the 🦉 register. No external asset — the mark is inline SVG so
 * it themes correctly on light + SOC. Renders as a link to `/` by default
 * (the Hall of Shame is home).
 */
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { OwlMascot, type OwlState } from "@/src/presentation/owliver/components/owl-mascot";

export type BrandLockupProps = {
  /** href for the lockup (default "/"). Pass null to render a non-link span. */
  href?: string | null;
  /** Hide the wordmark, show only the owl mark. */
  markOnly?: boolean;
  size?: "sm" | "md" | "lg";
  /** Owl mascot state (e.g. "alert" on the theater header). */
  owlState?: OwlState;
  className?: string;
};

const MARK_SIZE: Record<NonNullable<BrandLockupProps["size"]>, number> = {
  sm: 28,
  md: 34,
  lg: 44,
};
const TEXT_SIZE: Record<NonNullable<BrandLockupProps["size"]>, string> = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-2xl",
};

export function BrandLockup({
  href = "/",
  markOnly = false,
  size = "md",
  owlState = "idle",
  className,
}: BrandLockupProps) {
  const content = (
    <span
      data-slot="brand-lockup"
      className={cn("inline-flex items-center gap-2 select-none", className)}
    >
      <OwlMascot state={owlState} size={MARK_SIZE[size]} />
      {!markOnly && (
        <span
          className={cn(
            "font-semibold tracking-tight text-foreground",
            TEXT_SIZE[size]
          )}
        >
          Owliver
        </span>
      )}
    </span>
  );

  if (href === null) return content;
  return (
    <Link
      href={href}
      aria-label="Owliver — inicio"
      className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {content}
    </Link>
  );
}
