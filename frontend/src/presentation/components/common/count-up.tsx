"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { duration, easeFn } from "@/src/application/lib/motion";

type CountUpProps = {
  /** Target value to count to. */
  to: number;
  /** Start value (default 0). */
  from?: number;
  durationMs?: number;
  decimals?: number;
  className?: string;
  /** Optional suffix/prefix, e.g. "%". */
  suffix?: string;
  prefix?: string;
};

/**
 * M3 Expressive count-up: animates a number from `from` to `to` on
 * `emphasized-decelerate` easing. Used for the grade/score reveal in reports.
 * Respects `prefers-reduced-motion` (jumps to the final value).
 */
export function CountUp({
  to,
  from = 0,
  durationMs = duration.extraLong,
  decimals = 0,
  className,
  suffix = "",
  prefix = "",
}: CountUpProps) {
  const reduced = useReducedMotion();
  const [value, setValue] = React.useState(from);

  React.useEffect(() => {
    if (reduced) {
      setValue(to);
      return;
    }
    let raf = 0;
    let start: number | null = null;
    const tick = (ts: number) => {
      if (start === null) start = ts;
      const t = Math.min(1, (ts - start) / durationMs);
      setValue(from + (to - from) * easeFn.emphasizedDecelerate(t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to, from, durationMs, reduced]);

  return (
    <span className={className}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}
