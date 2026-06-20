"use client";

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/src/application/lib/utils";

/**
 * Shared styling for row-style cards (fields, validation rules, etc.):
 * - Consistent height via py-2.5
 * - Subtle bottom border between rows
 * - Hover highlight
 * - Horizontal layout with gap-2
 *
 * Wrap a list in <BaseListContainer> to get the rounded + bordered look.
 */
interface BaseListRowProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function BaseListRow({
  children,
  className,
  ...props
}: BaseListRowProps) {
  return (
    <div
      {...props}
      className={cn(
        "group flex items-center gap-2 py-2.5 px-3 border-b border-border/50 bg-background hover:bg-muted/30 transition-colors",
        className
      )}
    >
      {children}
    </div>
  );
}

interface BaseListContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function BaseListContainer({
  children,
  className,
  ...props
}: BaseListContainerProps) {
  return (
    <div
      {...props}
      className={cn(
        "rounded-md border border-border/50 overflow-hidden [&>*:last-child]:border-b-0",
        className
      )}
    >
      {children}
    </div>
  );
}
