#!/usr/bin/env python3
"""Simple webhook debug server.

Listens on a port (default 5000), prints every incoming request to the
terminal — method, path, query string, headers and body (pretty-printing
JSON when possible) — and always responds ``200 OK``.

Pure standard library, no dependencies, so it runs with any ``python3``.
Typically exposed publicly via a Cloudflare quick tunnel to inspect real
webhook deliveries:

    just webhook-tunnel        # server + public https://*.trycloudflare.com URL
    just webhook-debug         # local only, http://localhost:5000

Port can be overridden with the ``PORT`` env var or the first CLI arg.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 5000
RULE = "─" * 72


class WebhookDebugHandler(BaseHTTPRequestHandler):
    # We print our own line per request; silence the default access log.
    def log_message(self, *args: object) -> None:  # noqa: D102
        pass

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        self._print_request(body)

        payload = b"OK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    # Every common verb is answered the same way.
    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _handle

    def _print_request(self, body: bytes) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n{RULE}")
        print(f"  {ts}   {self.command} {self.path}")
        print(f"  from {self.client_address[0]}:{self.client_address[1]}")
        print(RULE)
        print("Headers:")
        for key, value in self.headers.items():
            print(f"  {key}: {value}")
        print("Body:")
        print(self._format_body(body))
        print(RULE, flush=True)

    @staticmethod
    def _format_body(body: bytes) -> str:
        if not body:
            return "  (empty)"
        text = body.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return "\n".join(f"  {line}" for line in text.splitlines())
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        return "\n".join(f"  {line}" for line in pretty.splitlines())


def main() -> int:
    raw_port = os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT)
    port = int(raw_port)

    server = ThreadingHTTPServer(("0.0.0.0", port), WebhookDebugHandler)
    print(f"Webhook debug server listening on http://0.0.0.0:{port}")
    print("Every request is printed below and answered with 200 OK. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
