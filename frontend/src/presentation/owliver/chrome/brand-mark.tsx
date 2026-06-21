/**
 * BrandMark — Owliver's real brand logo (the owl app-icon, `public/owliver-logo-*.png`).
 * This is the static, themeable wordmark companion shown in lockups, nav and auth —
 * NOT the animated `OwlMascot` (which conveys live scan state in the theater).
 *
 * Theme-aware: the light-theme art is a dark container (`owliver-logo-light.png`),
 * the dark/SOC art is a pale container (`owliver-logo-dark.png`). Both are rendered
 * and toggled with CSS so the swap is instant and SSR-safe (no theme-flash). `.soc`
 * is a dark surface applied via its own class, so it gets the same treatment as `.dark`.
 */
import Image from "next/image";

import { cn } from "@/src/application/lib/utils";

export type BrandMarkProps = {
  /** Rendered size in px (square). */
  size?: number;
  className?: string;
  /** Eager-load for above-the-fold lockups (nav, auth). */
  priority?: boolean;
};

export function BrandMark({ size = 34, className, priority }: BrandMarkProps) {
  return (
    <span
      data-slot="brand-mark"
      aria-hidden="true"
      className={cn("relative inline-block shrink-0 select-none", className)}
      style={{ width: size, height: size }}
    >
      {/* Light theme → dark-container logo */}
      <Image
        src="/owliver-logo-light.png"
        alt=""
        width={size}
        height={size}
        priority={priority}
        className="block dark:hidden [.soc_&]:hidden"
      />
      {/* Dark / SOC theme → pale-container logo */}
      <Image
        src="/owliver-logo-dark.png"
        alt=""
        width={size}
        height={size}
        priority={priority}
        className="absolute inset-0 hidden dark:block [.soc_&]:block"
      />
    </span>
  );
}
