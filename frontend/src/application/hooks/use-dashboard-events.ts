"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { subscribeSSE } from "@/src/infrastructure/http/sse";

import { queryKeys } from "./queries/keys";

type DashboardSection = "overview" | "processing";

interface DashboardEventPayload {
  type: string;
  tenantId?: string;
  affects?: DashboardSection[];
  payload?: Record<string, unknown>;
}

const DEFAULT_AFFECTS: DashboardSection[] = ["overview", "processing"];

/**
 * Subscribes to `/api/v1/dashboard/events` and invalidates the matching
 * TanStack Query cache slice when an event arrives. The stream itself
 * never carries dashboard data — it is purely an invalidation bus, so
 * the body of each event is small.
 *
 * The hook mounts once per dashboard session (see `dashboard/page.tsx`).
 * The underlying `subscribeSSE` client owns the connection lifecycle:
 * exponential-backoff reconnects, zombie-connection watchdog, and
 * cleanup on unmount via the returned AbortController.
 *
 * On reconnect we deliberately do NOT replay missed events — the
 * cheapest recovery is to invalidate everything once, which forces a
 * fresh REST fetch of whatever the user is currently looking at.
 */
export function useDashboardEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const controller = new AbortController();

    const cleanup = subscribeSSE("/api/v1/dashboard/events", {
      signal: controller.signal,
      onEvent({ type, data }) {
        if (type === "ready") {
          // Fresh connection (initial or reconnect). Invalidate both tabs
          // to converge on the latest state without relying on a replay
          // window from the backend.
          for (const section of DEFAULT_AFFECTS) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.dashboard.section(section),
            });
          }
          return;
        }
        if (type === "heartbeat") return;
        if (!data || data === "{}") return;

        let event: DashboardEventPayload;
        try {
          event = JSON.parse(data) as DashboardEventPayload;
        } catch {
          // Malformed payload: invalidate everything as a safe default.
          for (const section of DEFAULT_AFFECTS) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.dashboard.section(section),
            });
          }
          return;
        }

        const affects =
          event.affects && event.affects.length > 0
            ? event.affects
            : DEFAULT_AFFECTS;

        for (const section of affects) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.dashboard.section(section),
          });
        }
      },
    });

    return () => {
      controller.abort();
      cleanup?.();
    };
  }, [queryClient]);
}
