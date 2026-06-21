import type * as React from "react";

/**
 * ShieldWeb — bespoke icon for the 🛡️ "Web / OWASP" dimension. A shield with an
 * inset check, drawn in the lucide visual language (24-grid, currentColor,
 * 1.8 round stroke) so it reads as one vocabulary with the rest of the icon set.
 * Inherits color from the surrounding text; size via `className` (e.g. size-4).
 */
export function ShieldWeb({
  className,
  strokeWidth = 1.8,
  ...props
}: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      <path d="M12 2.5 4.75 5.4v6.05c0 4.2 3.05 7.27 7.25 8.55 4.2-1.28 7.25-4.35 7.25-8.55V5.4L12 2.5Z" />
      <path d="m8.85 11.9 2.15 2.15 4.15-4.4" />
    </svg>
  );
}
