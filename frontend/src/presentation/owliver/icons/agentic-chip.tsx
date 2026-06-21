import type * as React from "react";

/**
 * AgenticChip — bespoke icon for the 🤖 "Agentic Surface" dimension (chatbots /
 * LLM widgets). A minimal assistant head: rounded module, antenna, two eyes and
 * a mouth — distinct from the shield, evoking an embedded AI agent. Same lucide
 * visual language (24-grid, currentColor, 1.8 round stroke); color/size inherit.
 */
export function AgenticChip({
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
      {/* antenna */}
      <path d="M12 4.4V6" />
      <circle cx="12" cy="3.4" r="1.05" fill="currentColor" stroke="none" />
      {/* head */}
      <rect x="4" y="6" width="16" height="13" rx="3.6" />
      {/* side ports */}
      <path d="M2 11.5v2.5" />
      <path d="M22 11.5v2.5" />
      {/* eyes */}
      <circle cx="9.2" cy="11.4" r="1.15" fill="currentColor" stroke="none" />
      <circle cx="14.8" cy="11.4" r="1.15" fill="currentColor" stroke="none" />
      {/* mouth */}
      <path d="M9.5 15.4h5" />
    </svg>
  );
}
