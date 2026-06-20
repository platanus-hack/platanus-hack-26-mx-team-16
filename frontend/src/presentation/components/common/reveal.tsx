"use client";

import * as React from "react";

import { useReducedMotion } from "@/src/application/hooks/use-reduced-motion";
import { cn } from "@/src/application/lib/utils";

type RevealProps = React.ComponentProps<"div"> & {
  /** Stagger delay in ms (e.g. index * 60 for a list). */
  delay?: number;
};

/**
 * Fade + spring-ish slide-up on mount, using the `m3-enter` keyframe
 * (emphasized-decelerate). For findings entering a feed, cards appearing, etc.
 * Respects `prefers-reduced-motion` (renders instantly, no transform).
 */
export function Reveal({ className, delay = 0, style, ...props }: RevealProps) {
  const reduced = useReducedMotion();
  return (
    <div
      data-slot="reveal"
      className={cn(!reduced && "animate-m3-enter", className)}
      style={reduced ? style : { animationDelay: `${delay}ms`, ...style }}
      {...props}
    />
  );
}
