"use client";

import { useEffect } from "react";

import type { RunSummary } from "@/src/domain/entities/run-summary";

import { useRunSummaryStore } from "../stores/run-summary-store";
import { useSummaryEvents } from "./use-summary-events";

interface UseRunSummaryOptions {
  runId: string | null;
  /** Subscribe to the SSE summary events for live updates. */
  enableSse?: boolean;
}

interface UseRunSummaryResult {
  summary: RunSummary | null;
  isLoading: boolean;
  isResynthesizing: boolean;
  error: string | null;
  reload: () => Promise<RunSummary | null>;
  resynthesize: (force?: boolean) => Promise<RunSummary | null>;
}

const NOOP = async (): Promise<RunSummary | null> => null;

export function useRunSummary({
  runId,
  enableSse = true,
}: UseRunSummaryOptions): UseRunSummaryResult {
  const {
    summariesByRun,
    loading,
    resynthesizing,
    errors,
    loadSummary,
    resynthesize,
    applyEventUpdate,
  } = useRunSummaryStore();

  useEffect(() => {
    if (!runId) return;
    void loadSummary(runId);
  }, [runId, loadSummary]);

  useSummaryEvents({
    runId: runId ?? null,
    baseUrl: "/api",
    enabled: enableSse && !!runId,
    onEvent: (ev) => {
      if (
        ev.type === "summary.verdict_ready" ||
        ev.type === "summary.narrative_completed" ||
        ev.type === "summary.failed"
      ) {
        void applyEventUpdate(ev.runId);
      }
    },
  });

  if (!runId) {
    return {
      summary: null,
      isLoading: false,
      isResynthesizing: false,
      error: null,
      reload: NOOP,
      resynthesize: NOOP,
    };
  }

  return {
    summary: summariesByRun[runId] ?? null,
    isLoading: !!loading[runId],
    isResynthesizing: !!resynthesizing[runId],
    error: errors[runId] ?? null,
    reload: () => loadSummary(runId),
    resynthesize: (force?: boolean) => resynthesize(runId, force),
  };
}
