/**
 * OwlMascot 🦉 — the product's heartbeat, NOT clipart (§F2, DESIGN.md §6). An
 * inline SVG owl with three motion states:
 *   - idle    — eyes closed (sleeping / queued).
 *   - running — eyes open + slow blink/tilt (watching).
 *   - alert   — Mercury-violet "owl-eyes" ignite + glow pulse (found something).
 *
 * Eye color is driven by the state, not hardcoded brand color: running → primary
 * (activity), alert → tertiary violet ("owl-eyes"). Honors reduced-motion (the
 * pulse/blink collapse to a static state). Works on light + SOC backgrounds
 * (uses `currentColor` for the body so it inherits the surface ink).
 */
"use client";

import { cn } from "@/src/application/lib/utils";

export type OwlState = "idle" | "running" | "alert";

export type OwlMascotProps = {
  state?: OwlState;
  size?: number;
  className?: string;
  /** Hide the decorative SVG from AT (default true — it has a label). */
  "aria-hidden"?: boolean;
};

const STATE_LABEL: Record<OwlState, string> = {
  idle: "Owliver en reposo",
  running: "Owliver vigilando",
  alert: "Owliver detectó algo",
};

/** Eye color per state — primary = activity, tertiary violet = alert. */
function eyeColor(state: OwlState): string {
  if (state === "alert") return "var(--tertiary, #8f7cff)";
  if (state === "running") return "var(--primary, #6858f2)";
  return "var(--outline, #8a8a95)";
}

export function OwlMascot({
  state = "idle",
  size = 48,
  className,
}: OwlMascotProps) {
  const eyes = eyeColor(state);
  const open = state !== "idle";

  return (
    <span
      data-slot="owl-mascot"
      data-state={state}
      role="img"
      aria-label={STATE_LABEL[state]}
      className={cn(
        "inline-flex items-center justify-center",
        state === "alert" && "animate-pulse-once rounded-full",
        className
      )}
      style={{ width: size, height: size, color: "var(--foreground)" }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        aria-hidden
      >
        {/* Glow halo (alert) */}
        {state === "alert" && (
          <circle cx="24" cy="24" r="22" fill={eyes} opacity="0.14" />
        )}
        {/* Body */}
        <path
          d="M24 6c-7.2 0-13 5.4-13 12.8 0 4.2 0 8.6 2.4 12.2C16 35.4 19.6 38 24 38s8-2.6 10.6-7c2.4-3.6 2.4-8 2.4-12.2C37 11.4 31.2 6 24 6Z"
          fill="currentColor"
          opacity="0.92"
        />
        {/* Ear tufts */}
        <path
          d="M14 10c.5-3 2-5 2-5s1.6 2.2 1.4 5.2M34 10c-.5-3-2-5-2-5s-1.6 2.2-1.4 5.2"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          opacity="0.7"
        />
        {/* Eye discs */}
        <circle cx="18.5" cy="20" r="5.4" fill="var(--card, #fff)" opacity="0.95" />
        <circle cx="29.5" cy="20" r="5.4" fill="var(--card, #fff)" opacity="0.95" />
        {/* Pupils (open) or closed lids (idle) */}
        {open ? (
          <>
            <circle cx="18.5" cy="20" r="2.8" fill={eyes} />
            <circle cx="29.5" cy="20" r="2.8" fill={eyes} />
            {state === "running" && (
              <>
                <circle cx="19.4" cy="19" r="0.9" fill="var(--card, #fff)" />
                <circle cx="30.4" cy="19" r="0.9" fill="var(--card, #fff)" />
              </>
            )}
          </>
        ) : (
          <>
            <path
              d="M14.5 20.5q4 2.5 8 0M25.5 20.5q4 2.5 8 0"
              stroke="var(--outline, #8a8a95)"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          </>
        )}
        {/* Beak */}
        <path
          d="M24 23.5l-2 3.5h4l-2-3.5Z"
          fill="var(--tertiary, #8f7cff)"
        />
      </svg>
    </span>
  );
}
