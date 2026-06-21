/**
 * `useScanStream` — opens the live-view SSE for a scan and feeds parsed events
 * into the theater store (§F6, 10-realtime-live-view). Replay-then-tail: on mount
 * it subscribes with `?since_seq=` and the store discards `seq <= lastSeq`, so a
 * reload repaints the whole run idempotently.
 *
 * The stream URL goes through the same-origin proxy (`/api/v1/scans/{id}/stream`)
 * so `X-Api-Key` is attached by `proxy.ts` and the session cookie travels with
 * `credentials: "same-origin"`. For private scans the caller may pass a
 * `streamToken` which is appended as `?stream_token=`.
 */
"use client";

import * as React from "react";

import { scanEventSchema } from "../schemas/sse";
import { subscribeSSE, type SSESubscription } from "../lib/subscribe-sse";
import { useTheaterStore } from "../stores/theater-store";

export type ConnectionState = "connecting" | "open" | "closed" | "error";

export type UseScanStreamOptions = {
  /** When false the stream is not opened (e.g. degraded/Plan-B mode). */
  enabled?: boolean;
  /** Replay cursor; defaults to 0 (replay everything). */
  sinceSeq?: number;
  /** Ephemeral one-time token for private scans (`?stream_token=`). */
  streamToken?: string;
  /** Base path override (tests). Defaults to the proxied v1 stream route. */
  basePath?: string;
};

export type UseScanStreamResult = {
  connection: ConnectionState;
  /** Last transport error, if any. */
  error: unknown;
};

export function useScanStream(
  scanId: string,
  options: UseScanStreamOptions = {}
): UseScanStreamResult {
  const {
    enabled = true,
    sinceSeq = 0,
    streamToken,
    basePath = "/api/v1/scans",
  } = options;

  const init = useTheaterStore((s) => s.init);
  const apply = useTheaterStore((s) => s.apply);

  const [connection, setConnection] =
    React.useState<ConnectionState>("connecting");
  const [error, setError] = React.useState<unknown>(null);

  React.useEffect(() => {
    if (!enabled || !scanId) return;

    init(scanId, sinceSeq);
    setConnection("connecting");
    setError(null);

    const url = streamToken
      ? `${basePath}/${scanId}/stream?stream_token=${encodeURIComponent(streamToken)}`
      : `${basePath}/${scanId}/stream`;

    const sub: SSESubscription = subscribeSSE(url, {
      sinceSeq,
      onOpen: () => setConnection("open"),
      onError: (e) => {
        setError(e);
        setConnection("error");
      },
      onClose: () => setConnection("closed"),
      onMessage: (msg) => {
        // Heartbeats / non-data frames carry no JSON.
        if (!msg.data) return;
        try {
          const parsed = scanEventSchema.parse(JSON.parse(msg.data));
          apply(parsed);
        } catch {
          // Ignore unparseable frames (defensive against contract drift).
        }
      },
    });

    return () => sub.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanId, enabled, sinceSeq, streamToken, basePath]);

  return { connection, error };
}
