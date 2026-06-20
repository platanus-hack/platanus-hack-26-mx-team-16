"use client";
// icons.tsx — minimal line icons (stroke = currentColor). One per phase kind.
import type * as React from "react";
import type { IconName } from "./types";

const PATHS: Record<IconName, string> = {
  ingest:
    "M12 3v9m0 0l-3.2-3.2M12 12l3.2-3.2 M4 15v3a1 1 0 001 1h14a1 1 0 001-1v-3",
  extract_text: "M7 3h7l4 4v14H7z M14 3v4h4 M10 12h6 M10 16h4",
  classify_pages:
    "M9 4h8a1 1 0 011 1v8 M5 8h8a1 1 0 011 1v9a1 1 0 01-1 1H5a1 1 0 01-1-1V9a1 1 0 011-1z",
  extract_fields:
    "M8 4H6a1 1 0 00-1 1v14a1 1 0 001 1h2 M16 4h2a1 1 0 011 1v14a1 1 0 01-1 1h-2 M10 9h4 M10 13h4",
  assess: "M4 16a8 8 0 0116 0 M12 16l4.5-4.5 M9 16h.01",
  validate_extraction:
    "M12 3l7 2.5v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V5.5L12 3z M9 11.5l2 2 4-4.2",
  finalize: "M6 3v18 M6 4.5h11l-2.2 3.2L17 11H6",
  await_documents:
    "M4 7.5a1 1 0 011-1h3.6l1.6 1.8H19a1 1 0 011 1v8.2a1 1 0 01-1 1H5a1 1 0 01-1-1z",
  extraction_gate: "M4 5h16l-6.2 7.2v5.3l-3.6-2v-3.3z",
  await_clarification:
    "M5 5h14a1 1 0 011 1v8a1 1 0 01-1 1H10l-4 3.5V15H5a1 1 0 01-1-1V6a1 1 0 011-1z M12 8.3a1.5 1.5 0 011.3 2.3c-.4.5-1.1.7-1.1 1.4 M12 13.6h.01",
  enrich:
    "M12 3a9 9 0 100 18 9 9 0 000-18z M3.5 12h17 M12 3c2.6 2.4 4 5.5 4 9s-1.4 6.6-4 9c-2.6-2.4-4-5.5-4-9s1.4-6.6 4-9z",
  analyze:
    "M5 7h7 M16 7h3 M14 7a2 2 0 11-4 0 2 2 0 014 0z M5 17h3 M12 17h7 M10 17a2 2 0 11-4 0 2 2 0 014 0z",
  approval:
    "M12 3l2.1 1.5 2.6-.2.8 2.5 2.1 1.5-1 2.4 1 2.4-2.1 1.5-.8 2.5-2.6-.2L12 21l-2.1-1.5-2.6.2-.8-2.5-2.1-1.5 1-2.4-1-2.4 2.1-1.5.8-2.5 2.6.2z M9.3 12l1.9 1.9 3.5-3.8",
  output: "M12 3l8 4-8 4-8-4 8-4z M4 12l8 4 8-4 M4 16.5l8 4 8-4",
  deliver: "M21 4L3 11l6 2.5L12 20l3-7z M9 13.5L21 4",
};

export interface PipeIconProps {
  name: IconName;
  size?: number;
  stroke?: number;
  style?: React.CSSProperties;
  className?: string;
}

export function PipeIcon({
  name,
  size = 18,
  stroke = 1.6,
  style,
  className,
}: PipeIconProps) {
  const d = PATHS[name];
  if (!d) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ display: "block", flexShrink: 0, ...style }}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
