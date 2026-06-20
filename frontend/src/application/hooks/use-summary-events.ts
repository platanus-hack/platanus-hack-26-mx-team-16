"use client";

import { useEffect, useRef } from "react";

import type {
  RunSummaryEvent,
  RunSummaryEventType,
} from "@/src/domain/entities/run-summary";
import { subscribeSSE } from "@/src/infrastructure/http/sse";

const KNOWN_TYPES: ReadonlySet<RunSummaryEventType> = new Set<RunSummaryEventType>([
  "summary.verdict_ready",
  "summary.narrative_started",
  "summary.narrative_completed",
  "summary.failed",
]);

interface RawEvent {
  type?: unknown;
  run_id?: unknown;
  runId?: unknown;
  payload?: unknown;
}

function pickString(obj: RawEvent, ...keys: Array<keyof RawEvent>): string | null {
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === "string" && value) return value;
  }
  return null;
}

function normalize(parsed: unknown): RunSummaryEvent | null {
  if (!parsed || typeof parsed !== "object") return null;
  const r = parsed as RawEvent;
  const type = typeof r.type === "string" ? (r.type as RunSummaryEventType) : null;
  if (!type || !KNOWN_TYPES.has(type)) return null;
  const runId = pickString(r, "run_id", "runId");
  if (!runId) return null;
  const payload =
    r.payload && typeof r.payload === "object"
      ? (r.payload as Record<string, unknown>)
      : {};
  return { type, runId, payload };
}

interface UseSummaryEventsOptions {
  runId: string | null;
  baseUrl: string;
  enabled?: boolean;
  onEvent: (event: RunSummaryEvent) => void;
}

export function useSummaryEvents({
  runId,
  baseUrl,
  enabled = true,
  onEvent,
}: UseSummaryEventsOptions): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!runId || !enabled) return undefined;
    const url = `${baseUrl}/v1/workflow-analysis-runs/${runId}/summary/events`;
    return subscribeSSE(url, {
      onEvent: ({ data }) => {
        try {
          const parsed = JSON.parse(data);
          const normalized = normalize(parsed);
          if (normalized) handlerRef.current(normalized);
        } catch {
          // ignore non-JSON frames (heartbeats, etc.)
        }
      },
    });
  }, [runId, baseUrl, enabled]);
}
