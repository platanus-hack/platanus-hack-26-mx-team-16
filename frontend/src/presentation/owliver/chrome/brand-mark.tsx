/**
 * BrandMark — Owliver's brand logo: the flat owl app-icon mark
 * (`public/owliver-icon-{black,white}.svg`, no elevation/shadow). This is the
 * static, themeable wordmark companion shown in lockups, nav and auth — NOT the
 * animated `OwlMascot` (which conveys live scan state in the theater).
 *
 * Theme-aware: the light-theme art is the dark-container mark (`owliver-icon-black.svg`),
 * the dark/SOC art is the white-container mark (`owliver-icon-white.svg`). Both are
 * rendered and toggled with CSS so the swap is instant and SSR-safe (no theme flash).
 * `.soc` is a dark surface applied via its own class, so it gets the same treatment
 * as `.dark`.
 *
 * Plain <img> (not next/image): the mark is a fixed-size static SVG that needs no
 * optimization, and the Next image optimizer rejects SVG unless `dangerouslyAllowSVG`
 * is enabled — so a direct <img> is the robust, config-free choice.
 */
import { cn } from "@/src/application/lib/utils";

export type BrandMarkProps = {
  /** Rendered size in px (square). */
  size?: number;
  className?: string;
  /** Eager-load for above-the-fold lockups (nav, auth). */
  priority?: boolean;
};

export function BrandMark({ size = 34, className, priority }: BrandMarkProps) {
  const loading = priority ? "eager" : "lazy";
  const fetchPriority = priority ? "high" : "auto";

  return (
    <span
      data-slot="brand-mark"
      aria-hidden="true"
      className={cn("relative inline-block shrink-0 select-none", className)}
      style={{ width: size, height: size }}
    >
      {/* Light theme → dark-container mark */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/owliver-icon-black.svg"
        alt=""
        width={size}
        height={size}
        loading={loading}
        fetchPriority={fetchPriority}
        className="block dark:hidden [.soc_&]:hidden"
      />
      {/* Dark / SOC theme → white-container mark */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/owliver-icon-white.svg"
        alt=""
        width={size}
        height={size}
        loading={loading}
        fetchPriority={fetchPriority}
        className="absolute inset-0 hidden dark:block [.soc_&]:block"
      />
    </span>
  );
}
