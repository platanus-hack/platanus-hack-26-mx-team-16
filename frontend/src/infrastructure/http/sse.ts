import { useSessionStore } from "@/src/application/contexts/session-store";
import { getCommonHeaders } from "@/src/infrastructure/requests";

type SSEHandler = (event: { type: string; data: string }) => void;
type UrlFactory = () => string;

/**
 * Lifecycle of an SSE subscription:
 * - `idle`         — before the first attempt, or after the master abort.
 * - `connecting`   — fetch in flight, no body yet.
 * - `connected`    — body is streaming; events are flowing.
 * - `reconnecting` — drop or transport error happened; backoff is running
 *                    before the next attempt.
 */
export type ConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting";

interface SubscribeOptions {
  onEvent: SSEHandler;
  onOpen?: () => void;
  onError?: (err: unknown) => void;
  /** Fires every time the connection lifecycle transitions. */
  onStateChange?: (state: ConnectionState) => void;
  signal?: AbortSignal;
  /** Base backoff in ms between reconnect attempts. Default 2000. */
  reconnectBaseDelay?: number;
  /** Max backoff in ms. Default 30000. */
  reconnectMaxDelay?: number;
  /**
   * Force reconnect when no bytes arrive for this many ms. Catches zombie
   * connections (TCP held open by an intermediate proxy with no traffic).
   * Set ≥ 2× the server heartbeat interval. Default 50000.
   */
  connectionWatchdogMs?: number;
}

/**
 * SSE subscriber that uses `fetch` so we can attach `Authorization` and
 * `X-Tenant` headers (native EventSource can't set headers).
 *
 * Automatically reconnects with exponential backoff when the connection drops,
 * until the returned cleanup function is called. Pass a factory function
 * instead of a string to recompute the URL (e.g. updated `since_seq`) on each
 * reconnect attempt.
 */
export function subscribeSSE(
  urlOrFactory: string | UrlFactory,
  options: SubscribeOptions
): () => void {
  const controller = new AbortController();
  const baseDelay = options.reconnectBaseDelay ?? 2000;
  const maxDelay = options.reconnectMaxDelay ?? 30000;
  const watchdogMs = options.connectionWatchdogMs ?? 50000;
  let attempt = 0;
  const getUrl: UrlFactory =
    typeof urlOrFactory === "function" ? urlOrFactory : () => urlOrFactory;

  // If caller passed an external signal, forward aborts to our controller.
  if (options.signal) {
    if (options.signal.aborted) controller.abort();
    else
      options.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
  }

  const emit = (state: ConnectionState) => options.onStateChange?.(state);

  async function connect(): Promise<void> {
    while (!controller.signal.aborted) {
      emit("connecting");

      // Per-connection controller so the watchdog can kill a stalled fetch
      // without taking down the outer loop.
      const inner = new AbortController();
      const propagate = () => inner.abort();
      if (controller.signal.aborted) inner.abort();
      else
        controller.signal.addEventListener("abort", propagate, { once: true });

      let watchdog: ReturnType<typeof setTimeout> | null = null;
      const armWatchdog = () => {
        if (watchdog) clearTimeout(watchdog);
        watchdog = setTimeout(() => inner.abort(), watchdogMs);
      };
      const clearWatchdog = () => {
        if (watchdog) {
          clearTimeout(watchdog);
          watchdog = null;
        }
      };

      try {
        const { tenant, accessToken } = useSessionStore.getState();
        const headers = {
          ...getCommonHeaders(tenant?.slug ?? null, accessToken ?? null),
          Accept: "text/event-stream",
        };

        armWatchdog();
        const response = await fetch(getUrl(), {
          method: "GET",
          headers,
          signal: inner.signal,
          credentials: "same-origin",
          cache: "no-store",
        });

        if (!response.ok || !response.body) {
          options.onError?.(new Error(`SSE HTTP ${response.status}`));
          if (!controller.signal.aborted) emit("reconnecting");
          await backoff();
          continue;
        }

        attempt = 0;
        options.onOpen?.();
        emit("connected");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          armWatchdog();
          const { value, done } = await reader.read();
          if (done) break;
          // sse_starlette emits CRLF separators per the SSE spec; normalize
          // to LF so the parser only has to deal with one line ending.
          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

          let sepIdx: number;
          while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
            const rawEvent = buffer.slice(0, sepIdx);
            buffer = buffer.slice(sepIdx + 2);
            const parsed = parseEvent(rawEvent);
            if (parsed) options.onEvent(parsed);
          }
        }

        // Stream closed cleanly — reconnect after small backoff.
        if (!controller.signal.aborted) {
          emit("reconnecting");
          await backoff();
        }
      } catch (err) {
        // Master abort: caller cleaned up, exit the loop.
        if (controller.signal.aborted) return;
        // Inner-only abort (watchdog timeout) or transport error → reconnect.
        options.onError?.(err);
        emit("reconnecting");
        await backoff();
      } finally {
        clearWatchdog();
        controller.signal.removeEventListener("abort", propagate);
      }
    }
    emit("idle");
  }

  function backoff(): Promise<void> {
    const delay = Math.min(maxDelay, baseDelay * 2 ** attempt);
    attempt += 1;
    return new Promise((resolve) => {
      const timer = setTimeout(resolve, delay);
      controller.signal.addEventListener(
        "abort",
        () => {
          clearTimeout(timer);
          resolve();
        },
        { once: true }
      );
    });
  }

  void connect();
  return () => controller.abort();
}

// Exported for unit tests. Internal — signature can change without notice.
export function parseEvent(raw: string): { type: string; data: string } | null {
  let type = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (!line || line.startsWith(":")) continue; // comment/heartbeat
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    const value = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "event") type = value;
    else if (field === "data") dataLines.push(value);
  }
  if (dataLines.length === 0) return null;
  return { type, data: dataLines.join("\n") };
}
