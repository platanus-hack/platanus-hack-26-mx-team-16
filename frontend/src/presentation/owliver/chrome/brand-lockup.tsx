/**
 * BrandLockup — Owliver's wordmark: the owl mark + the "Owliver" name. The mark is
 * the real brand logo (`BrandMark`, theme-aware PNG) for the resting brand state.
 * When an active `owlState` ("running"/"alert") is requested the animated `OwlMascot`
 * is used instead, since there the motion conveys live status rather than branding.
 * Renders as a link to `/` by default (the public landing is home).
 */
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { BrandMark } from "@/src/presentation/owliver/chrome/brand-mark";
import {
  OwlMascot,
  type OwlState,
} from "@/src/presentation/owliver/components/owl-mascot";

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
  md: 40,
  lg: 44,
};
const TEXT_SIZE: Record<NonNullable<BrandLockupProps["size"]>, string> = {
  sm: "text-base",
  md: "text-xl",
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
      {owlState === "idle" ? (
        <BrandMark size={MARK_SIZE[size]} priority />
      ) : (
        <OwlMascot state={owlState} size={MARK_SIZE[size]} />
      )}
      {!markOnly && (
        <span
          className={cn(
            "font-brand font-bold tracking-tight",
            TEXT_SIZE[size]
          )}
        >
          <span className="text-primary">Owl</span>
          <span className="text-foreground">iver</span>
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
