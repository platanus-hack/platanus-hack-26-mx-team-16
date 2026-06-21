/**
 * `subscribeSSE` — a fetch-based Server-Sent Events reader (NOT native
 * `EventSource`). We use fetch + a streaming body reader because:
 *
 * - auth is by HttpOnly cookie (`credentials: "same-origin"`), and we want it to
 *   work behind the same-origin BFF/proxy without custom headers;
 * - we need replay-then-tail via a `?since_seq=` cursor and `Last-Event-ID`
 *   compatibility, plus reconnect with the advanced cursor.
 *
 * The contract (10-realtime-live-view): events carry a monotonic `seq` (also the
 * SSE `id:`). On (re)connect we send `?since_seq=lastSeq`; the server replays all
 * `seq > cursor` from Postgres then tails. The consumer (theater store) drops
 * `seq <= lastSeq`, so reconnect overlap is harmless.
 *
 * Terminal `done`/`error` events stop the stream. Network drops auto-reconnect
 * with backoff using the last seen seq as the cursor.
 */

export type SSEMessage = {
  /** SSE `event:` field (defaults to "message"). */
  event: string;
  /** SSE `data:` payload (joined multi-line). */
  data: string;
  /** SSE `id:` field — for us this is the monotonic `seq`. */
  id: string | null;
};

export type SubscribeSSEOptions = {
  /** Called for every parsed SSE message. */
  onMessage: (msg: SSEMessage) => void;
  /** Called once the stream is opened (HTTP 200, body readable). */
  onOpen?: () => void;
  /** Called on a (possibly recoverable) transport error. */
  onError?: (error: unknown) => void;
  /** Called when the stream closes for good (terminal event or aborted). */
  onClose?: () => void;
  /** Initial replay cursor; appended as `?since_seq=`. */
  sinceSeq?: number;
  /**
   * Predicate that, given a message, returns true if it is TERMINAL (closes the
   * stream). Defaults to closing on `event === "done" | "error"`.
   */
  isTerminal?: (msg: SSEMessage) => boolean;
  /** Max reconnect attempts on transport drop (default 5). */
  maxRetries?: number;
};

export type SSESubscription = {
  /** Stop the stream and prevent further reconnects. */
  close: () => void;
  /** The highest `id`/seq observed so far (the live cursor). */
  lastEventId: () => string | null;
};

const TERMINAL_EVENTS = new Set(["done", "error"]);

function defaultIsTerminal(msg: SSEMessage): boolean {
  return TERMINAL_EVENTS.has(msg.event);
}

/**
 * Parse a raw SSE chunk buffer into complete messages, returning the leftover
 * (incomplete) tail. Messages are separated by a blank line.
 */
function parseSSEBuffer(buffer: string): {
  messages: SSEMessage[];
  rest: string;
} {
  const messages: SSEMessage[] = [];
  const parts = buffer.split(/\r?\n\r?\n/);
  const rest = parts.pop() ?? "";

  for (const block of parts) {
    if (!block.trim()) continue;
    let event = "message";
    let id: string | null = null;
    const dataLines: string[] = [];

    for (const rawLine of block.split(/\r?\n/)) {
      if (!rawLine || rawLine.startsWith(":")) continue; // comment/heartbeat
      const idx = rawLine.indexOf(":");
      const field = idx === -1 ? rawLine : rawLine.slice(0, idx);
      let value = idx === -1 ? "" : rawLine.slice(idx + 1);
      if (value.startsWith(" ")) value = value.slice(1);

      switch (field) {
        case "event":
          event = value;
          break;
        case "data":
          dataLines.push(value);
          break;
        case "id":
          id = value;
          break;
      }
    }

    messages.push({ event, data: dataLines.join("\n"), id });
  }

  return { messages, rest };
}

/**
 * Open an SSE stream against `url` (a same-origin path, e.g.
 * `/api/v1/scans/{id}/stream`). Returns a handle you can `close()`.
 */
export function subscribeSSE(
  url: string,
  options: SubscribeSSEOptions
): SSESubscription {
  const {
    onMessage,
    onOpen,
    onError,
    onClose,
    sinceSeq = 0,
    isTerminal = defaultIsTerminal,
    maxRetries = 5,
  } = options;

  const controller = new AbortController();
  let closed = false;
  let cursor = sinceSeq;
  let retries = 0;

  const buildUrl = () => {
    const u = new URL(url, window.location.origin);
    if (cursor > 0) u.searchParams.set("since_seq", String(cursor));
    return u.toString();
  };

  const run = async () => {
    while (!closed) {
      try {
        const res = await fetch(buildUrl(), {
          method: "GET",
          credentials: "same-origin",
          headers: {
            Accept: "text/event-stream",
            // Last-Event-ID kept for server compat with the seq cursor.
            ...(cursor > 0 ? { "Last-Event-ID": String(cursor) } : {}),
          },
          cache: "no-store",
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`SSE HTTP ${res.status}`);
        }

        retries = 0;
        onOpen?.();

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!closed) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const { messages, rest } = parseSSEBuffer(buffer);
          buffer = rest;

          for (const msg of messages) {
            if (msg.id) {
              const n = Number(msg.id);
              if (Number.isFinite(n) && n > cursor) cursor = n;
            }
            onMessage(msg);
            if (isTerminal(msg)) {
              closed = true;
              onClose?.();
              return;
            }
          }
        }

        // Body ended without a terminal event → reconnect from the cursor.
        if (!closed) throw new Error("SSE stream ended; reconnecting");
      } catch (err) {
        if (closed || controller.signal.aborted) break;
        onError?.(err);
        retries += 1;
        if (retries > maxRetries) {
          closed = true;
          onClose?.();
          break;
        }
        const backoff = Math.min(1000 * 2 ** (retries - 1), 8000);
        await new Promise((r) => setTimeout(r, backoff));
      }
    }
  };

  void run();

  return {
    close: () => {
      if (closed) return;
      closed = true;
      controller.abort();
      onClose?.();
    },
    lastEventId: () => (cursor > 0 ? String(cursor) : null),
  };
}
