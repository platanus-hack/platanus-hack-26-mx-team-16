"use client";

import { cn } from "@/src/application/lib/utils";

export interface CitationLike {
  document_id: string;
  document_type_slug: string;
  field_path: string;
  value?: string | null;
  sub_check_id?: string | null;
}

interface CitationChipProps {
  citation: CitationLike;
  onNavigate?: (citation: CitationLike) => void;
  className?: string;
}

export function CitationChip({
  citation,
  onNavigate,
  className,
}: CitationChipProps) {
  const label = `@${citation.document_type_slug}${
    citation.field_path ? `.${citation.field_path}` : ""
  }`;
  const tooltip =
    citation.value !== null && citation.value !== undefined
      ? `${label} = ${citation.value}`
      : label;
  const interactive = typeof onNavigate === "function";

  return (
    <span
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={interactive ? () => onNavigate?.(citation) : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onNavigate?.(citation);
              }
            }
          : undefined
      }
      title={tooltip}
      className={cn(
        "inline-flex h-5 max-w-[260px] items-center gap-1 rounded border border-border/70 px-1.5 font-mono text-[11px]",
        "text-muted-foreground/90 transition-colors",
        interactive && "cursor-pointer hover:border-foreground/40 hover:text-foreground",
        className
      )}
    >
      <span aria-hidden className="text-muted-foreground/60">
        ↳
      </span>
      <span className="truncate">{label}</span>
    </span>
  );
}
