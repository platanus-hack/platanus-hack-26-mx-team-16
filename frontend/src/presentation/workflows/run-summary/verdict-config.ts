import type { Verdict } from "@/src/domain/entities/run-summary";

export interface VerdictTone {
  label: string;
  text: string;
  border: string;
  glyph: string;
  /** Tailwind class for a single dot of this verdict (used in counts). */
  dot: string;
}

export const VERDICT_TONE: Record<Verdict, VerdictTone> = {
  PASS: {
    label: "Pass",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-600/60 dark:border-emerald-400/60",
    glyph: "PASS",
    dot: "bg-emerald-600 dark:bg-emerald-400",
  },
  FAIL: {
    label: "Fail",
    text: "text-rose-600 dark:text-rose-400",
    border: "border-rose-600/60 dark:border-rose-400/60",
    glyph: "FAIL",
    dot: "bg-rose-600 dark:bg-rose-400",
  },
  REVIEW: {
    label: "Review",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-500/60 dark:border-amber-400/60",
    glyph: "REVIEW",
    dot: "bg-amber-500 dark:bg-amber-400",
  },
};

export type Polarity = "PASS" | "FAIL" | "NEUTRAL";

export const POLARITY_TONE: Record<Polarity, { label: string; bar: string; dot: string }> = {
  PASS: {
    label: "Pass",
    bar: "bg-emerald-600 dark:bg-emerald-400",
    dot: "bg-emerald-600 dark:bg-emerald-400",
  },
  FAIL: {
    label: "Fail",
    bar: "bg-rose-600 dark:bg-rose-400",
    dot: "bg-rose-600 dark:bg-rose-400",
  },
  NEUTRAL: {
    label: "Neutral",
    bar: "bg-zinc-400 dark:bg-zinc-500",
    dot: "bg-zinc-400 dark:bg-zinc-500",
  },
};

export type Severity = "BLOCKER" | "MAJOR" | "MINOR" | "INFO";

export const SEVERITY_TONE: Record<Severity, { label: string; dot: string }> = {
  BLOCKER: { label: "Blocker", dot: "bg-rose-600 dark:bg-rose-400" },
  MAJOR: { label: "Major", dot: "bg-amber-500 dark:bg-amber-400" },
  MINOR: { label: "Minor", dot: "bg-zinc-500 dark:bg-zinc-400" },
  INFO: { label: "Info", dot: "bg-sky-500 dark:bg-sky-400" },
};
