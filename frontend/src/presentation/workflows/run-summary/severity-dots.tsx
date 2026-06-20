"use client";

import { cn } from "@/src/application/lib/utils";

import { SEVERITY_TONE, type Severity } from "./verdict-config";

interface SeverityDotsProps {
  counts: Record<string, number>;
  className?: string;
}

const ORDER: Severity[] = ["BLOCKER", "MAJOR", "MINOR", "INFO"];
const MAX_DOTS = 5;

export function SeverityDots({ counts, className }: SeverityDotsProps) {
  const visible = ORDER.filter((k) => (counts[k] ?? 0) > 0);
  if (visible.length === 0) return null;

  return (
    <ul
      className={cn(
        "flex flex-wrap items-center gap-x-5 gap-y-2 text-xs",
        className
      )}
    >
      {visible.map((key) => {
        const value = counts[key] ?? 0;
        const tone = SEVERITY_TONE[key];
        const dots = Math.min(value, MAX_DOTS);
        const overflow = value > MAX_DOTS;
        return (
          <li key={key} className="flex items-center gap-2">
            <span aria-hidden className="flex items-center gap-0.5">
              {Array.from({ length: dots }).map((_, idx) => (
                <span
                  key={idx}
                  className={cn("h-1.5 w-1.5 rounded-full", tone.dot)}
                />
              ))}
              {overflow ? (
                <span className="ml-0.5 font-mono text-[10px] text-muted-foreground/80">
                  +
                </span>
              ) : null}
            </span>
            <span className="font-mono uppercase tracking-[0.15em] text-muted-foreground/80">
              {tone.label}
            </span>
            <span className="font-medium tabular-nums">{value}</span>
          </li>
        );
      })}
    </ul>
  );
}
