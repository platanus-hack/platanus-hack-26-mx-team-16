/**
 * FindingFeedItem — one finding as it lands in the live SOC feed (§F6) AND as a
 * dense row elsewhere. Header = SeverityChip + OWASP/LLM category + title. In
 * `live` mode it enters with the M3 `Reveal` (fade + spring slide-up); critical
 * findings pulse once in red (`animate-pulse-once`) to demand the eye.
 *
 * Color/severity come from the shared `SeverityChip` (icon + text, not color
 * alone → §F12 a11y). The category code (A01–A10 / LLM01–LLM10) renders in mono.
 * Works on both the light shell and the dark SOC theater (theme tokens only).
 */
"use client";

import { cn } from "@/src/application/lib/utils";
import type { Severity } from "@/src/application/owliver/schemas/api";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { SeverityChip } from "@/src/presentation/owliver/components/severity-chip";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

export type FindingFeedItemProps = {
  severity: Severity;
  title: string;
  /** OWASP A01–A10 or OWASP-LLM LLM01–LLM10. */
  category?: string;
  /** "owasp" | "agentic" — shown as a small dimension tag. */
  source?: "owasp" | "agentic";
  /** Spring-in on mount (live feed). Off → static row (report). */
  live?: boolean;
  /** Stagger delay for the Reveal (e.g. index * 50). */
  delay?: number;
  className?: string;
  onClick?: () => void;
};

const SOURCE_META: Record<
  "owasp" | "agentic",
  { label: string; Icon: typeof ShieldWeb }
> = {
  owasp: { label: "Web", Icon: ShieldWeb },
  agentic: { label: "Agéntico", Icon: AgenticChip },
};

export function FindingFeedItem({
  severity,
  title,
  category,
  source,
  live = false,
  delay = 0,
  className,
  onClick,
}: FindingFeedItemProps) {
  const critical = severity === "critical";

  const content = (
    <>
      <SeverityChip severity={severity} iconOnly size="sm" className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex flex-wrap items-center gap-2">
          {category && (
            <span className="rounded bg-surface-container px-1.5 py-0.5 font-mono text-[10px] font-semibold text-on-surface-variant">
              {category}
            </span>
          )}
          {source &&
            (() => {
              const { label, Icon } = SOURCE_META[source];
              return (
                <span className="inline-flex items-center gap-1 text-[11px] text-on-surface-variant">
                  <Icon className="size-3" />
                  {label}
                </span>
              );
            })()}
        </div>
        <p className="text-sm font-medium leading-snug text-foreground">
          {title}
        </p>
      </div>
    </>
  );

  const itemClassName = cn(
    "flex w-full items-start gap-3 rounded-xl border border-outline-variant bg-card p-3 text-left shadow-xs transition-colors duration-150",
    onClick &&
      "cursor-pointer hover:bg-surface-container-low focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    critical && live && "animate-pulse-once",
    className
  );

  const body = onClick ? (
    <button
      type="button"
      data-slot="finding-feed-item"
      data-severity={severity}
      onClick={onClick}
      className={itemClassName}
    >
      {content}
    </button>
  ) : (
    <div
      data-slot="finding-feed-item"
      data-severity={severity}
      className={itemClassName}
    >
      {content}
    </div>
  );

  if (!live) return body;
  return <Reveal delay={delay}>{body}</Reveal>;
}
