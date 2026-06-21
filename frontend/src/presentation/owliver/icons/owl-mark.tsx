import type * as React from "react";

/**
 * OwlMark — bespoke inline brand glyph (replaces the 🦉 used next to the
 * "Owliver" wordmark in lockups, footer and copy). A compact owl face: ear
 * tufts, round head, two wide eyes and a beak. Same lucide visual language
 * (24-grid, currentColor, round stroke). For the animated theater mascot use
 * `OwlMascot` instead — this is the static text-companion mark.
 */
export function OwlMark({
  className,
  strokeWidth = 1.7,
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
      {/* ear tufts */}
      <path d="M6 5.2 8.2 7.6" />
      <path d="M18 5.2 15.8 7.6" />
      {/* head / body */}
      <path d="M12 4.9c-3.9 0-6.4 3-6.4 7.2 0 4 2.7 6.9 6.4 6.9s6.4-2.9 6.4-6.9c0-4.2-2.5-7.2-6.4-7.2Z" />
      {/* eyes */}
      <circle cx="9.3" cy="11" r="1.85" />
      <circle cx="14.7" cy="11" r="1.85" />
      <circle cx="9.3" cy="11" r="0.35" fill="currentColor" stroke="none" />
      <circle cx="14.7" cy="11" r="0.35" fill="currentColor" stroke="none" />
      {/* beak */}
      <path d="M12 13.1v1.5" />
    </svg>
  );
}
