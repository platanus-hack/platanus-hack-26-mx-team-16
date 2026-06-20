"use client";

import { Check } from "lucide-react";
import { cn } from "@/src/application/lib/utils";

interface StepperProps {
  current: number;
  steps: Array<{ key: string; label: string }>;
}

export function Stepper({ current, steps }: StepperProps) {
  return (
    <ol className="flex items-center gap-3" aria-label="Wizard progress">
      {steps.map((step, idx) => {
        const isDone = idx < current;
        const isActive = idx === current;
        return (
          <li key={step.key} className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-semibold tabular-nums transition-colors",
                isDone &&
                  "bg-primary border-primary text-primary-foreground",
                isActive &&
                  !isDone &&
                  "border-primary text-primary bg-primary/10",
                !isDone &&
                  !isActive &&
                  "border-border text-muted-foreground bg-muted/40",
              )}
            >
              {isDone ? <Check className="h-3.5 w-3.5" /> : idx + 1}
            </div>
            <span
              className={cn(
                "font-mono text-[10px] uppercase tracking-[0.18em]",
                isActive
                  ? "text-foreground"
                  : isDone
                    ? "text-foreground/80"
                    : "text-muted-foreground",
              )}
            >
              {step.label}
            </span>
            {idx < steps.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "h-px w-8 transition-colors",
                  isDone ? "bg-primary" : "bg-border",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
