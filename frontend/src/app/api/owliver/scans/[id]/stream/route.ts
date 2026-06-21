/**
 * BFF: GET /api/owliver/scans/{id}/stream → backend GET /v1/scans/{id}/stream
 * (§F6, 10-realtime-live-view). Proxies the upstream SSE body straight through
 * (replay-then-tail), forwarding `?since_seq=` / `Last-Event-ID`.
 *
 * Streaming correctness (the whole point of a dedicated route, vs. the generic
 * proxy): we set `X-Accel-Buffering: no` + `Cache-Control: no-transform` and pin
 * `Content-Encoding: identity` so neither nginx nor Next buffers/compresses the
 * stream — events must reach the browser the instant the backend emits them.
 *
 * Offline / fixture fallback: when the backend is unreachable (no live worker in
 * the demo), we synthesize the SSE wire from `scanEventsFixture` on a timer so the
 * theater still plays the full run (the cinematic replay the demo depends on).
 */
import type { NextRequest } from "next/server";

import { COOKIE_ACCESS_TOKEN } from "@/src/constants";
import { Settings } from "@/src/settings";
import { buildScanEventsFor } from "@/src/application/owliver/fixtures";
import {
  TERMINAL_EVENT_TYPES,
  type ScanEvent,
} from "@/src/application/owliver/schemas/sse";

// SSE must never be statically optimized or buffered.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const SSE_HEADERS: Record<string, string> = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  // Disable proxy buffering (nginx / Cloudflare) so frames flush immediately.
  "X-Accel-Buffering": "no",
  // Defeat any compression middleware that would buffer the stream.
  "Content-Encoding": "identity",
};

function frame(type: string, id: number, data: unknown): string {
  return `event: ${type}\nid: ${id}\ndata: ${JSON.stringify(data)}\n\n`;
}

/**
 * Replay a synthesized event sequence as an SSE stream on a timer. `events` is
 * already filtered by `since_seq` so reloads are idempotent like the real
 * backend. `keepOpen` (an in-flight scan whose sequence has no terminal event)
 * holds the connection open after the last event instead of closing it — the
 * client treats a closed body without a terminal as a drop and reconnects
 * (subscribe-sse), so closing here would trigger a reconnect storm. A heartbeat
 * keeps proxies from idling the held-open socket.
 */
function fixtureStream(
  events: ScanEvent[],
  keepOpen: boolean
): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  let i = 0;
  // The replay is driven by a self-rescheduling timer. If the client
  // disconnects mid-run, the stream is cancelled and the controller closed —
  // but a pending tick would still fire and call enqueue() on the closed
  // controller, throwing ERR_INVALID_STATE. Track the timer + a closed flag so
  // cancel() can stop it and tick() can bail.
  let timer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  return new ReadableStream<Uint8Array>({
    start(controller) {
      // Prime the connection so the client flips to "open" instantly.
      controller.enqueue(enc.encode(": owliver-stream-open\n\n"));

      const heartbeat = () => {
        if (closed) return;
        try {
          controller.enqueue(enc.encode(": keep-alive\n\n"));
        } catch {
          closed = true;
          return;
        }
        timer = setTimeout(heartbeat, 15_000);
      };

      const tick = () => {
        if (closed) return;
        if (i >= events.length) {
          if (keepOpen) {
            // In-flight scan: nothing more to replay, but the run isn't over.
            // Hold the connection open (heartbeat) so the client keeps tailing.
            timer = setTimeout(heartbeat, 15_000);
            return;
          }
          closed = true;
          controller.close();
          return;
        }
        const e = events[i++];
        try {
          controller.enqueue(enc.encode(frame(e.type, e.seq, e)));
        } catch {
          // Controller closed underneath us (client gone) — stop replaying.
          closed = true;
          return;
        }
        // Cadence: fast enough to feel live, slow enough to read the tension.
        const delay = e.type === "done" ? 400 : 650;
        timer = setTimeout(tick, delay);
      };
      // Small lead-in before the first event lands.
      timer = setTimeout(tick, 350);
    },
    cancel() {
      // Client disconnected: kill the timer so tick()/heartbeat() never touch
      // the now-closed controller.
      closed = true;
      if (timer) clearTimeout(timer);
    },
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const url = new URL(request.url);
  const sinceSeq = Number.parseInt(url.searchParams.get("since_seq") ?? "0", 10);
  const streamToken = url.searchParams.get("stream_token");

  // Build the upstream URL preserving the replay cursor + private-scan token.
  const upstream = new URL(`${Settings.apiBaseUrl}/v1/scans/${id}/stream`);
  if (Number.isFinite(sinceSeq) && sinceSeq > 0) {
    upstream.searchParams.set("since_seq", String(sinceSeq));
  }
  if (streamToken) upstream.searchParams.set("stream_token", streamToken);

  const lastEventId = request.headers.get("last-event-id");

  try {
    const accessToken = request.cookies.get(COOKIE_ACCESS_TOKEN)?.value;
    const headers: Record<string, string> = {
      Accept: "text/event-stream",
      "X-Api-Key": Settings.apiKey,
    };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (lastEventId) headers["Last-Event-ID"] = lastEventId;

    // Bound how long we wait for the upstream *headers*. A hung backend (e.g.
    // uvicorn --reload stuck "waiting for connections to close") accepts the TCP
    // connection but never replies — without this guard the proxy hangs forever
    // and the client sits on "conectando…" instead of falling back to the
    // fixture replay below. Linked to request.signal so a client disconnect
    // still aborts. Cleared once headers arrive, so the streaming body itself is
    // never time-limited.
    const connect = new AbortController();
    const onAbort = () => connect.abort();
    request.signal.addEventListener("abort", onAbort);
    const connectTimeout = setTimeout(() => connect.abort(), 4000);

    let res: Response;
    try {
      res = await fetch(upstream.toString(), {
        headers,
        // Stream the response; do not let fetch buffer.
        cache: "no-store",
        signal: connect.signal,
      });
    } finally {
      clearTimeout(connectTimeout);
      request.signal.removeEventListener("abort", onAbort);
    }

    if (res.ok && res.body) {
      return new Response(res.body, { status: 200, headers: SSE_HEADERS });
    }
    // Forward a real 404 (private scan, no permission) — don't fall back to fixtures.
    if (res.status === 404) {
      return new Response("Not found", { status: 404 });
    }
  } catch {
    // Backend unreachable, hung, or slow to respond → fall through to the
    // fixture replay below so the demo theater always plays.
  }

  // Offline replay: synthesize THIS scan's events (host-correct, matching its
  // report) instead of one generic reel. An in-flight scan (no terminal event in
  // its sequence) holds the connection open so the client tails rather than
  // reconnecting.
  const cursor = Number.isFinite(sinceSeq) ? sinceSeq : 0;
  const allEvents = buildScanEventsFor(id);
  const filtered = allEvents.filter((e) => e.seq > cursor);
  const lastIsTerminal =
    allEvents.length > 0 &&
    TERMINAL_EVENT_TYPES.has(allEvents[allEvents.length - 1].type);

  // Reconnect past the end of a finished run: the slice is empty but the run IS
  // over. Re-send just the terminal event so the client sees a terminal frame and
  // closes cleanly, instead of reading a body-end-without-terminal and entering a
  // reconnect loop (subscribe-sse). The store's `seq <= lastSeq` guard makes
  // re-applying the terminal event idempotent.
  const events =
    filtered.length === 0 && lastIsTerminal
      ? [allEvents[allEvents.length - 1]]
      : filtered;

  return new Response(fixtureStream(events, !lastIsTerminal), {
    status: 200,
    headers: SSE_HEADERS,
  });
}
