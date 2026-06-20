"""
Middleware for converting camelCase request bodies to snake_case.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import ClientDisconnect, Request
from starlette.responses import Response

from src.common.application.logging import get_logger

logger = get_logger(__name__)


class CamelCaseToSnakeCaseMiddleware(BaseHTTPMiddleware):
    """
    Convert incoming camelCase JSON keys to snake_case.

    Multipart uploads (and any non-JSON content type) are passed through
    untouched — buffering a 100 MB upload through `request.body()` only
    to flip a few key names is wasteful and historically caused
    `ClientDisconnect` errors to bubble up here when the upstream proxy
    gave up. We also catch `ClientDisconnect` defensively so an aborted
    request doesn't crash the middleware stack.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Webhooks need raw body access for signature verification.
        if "/webhooks/" in request.url.path:
            return await call_next(request)

        content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            try:
                body = await request.body()
            except ClientDisconnect:
                # Client gave up mid-upload (proxy timeout, navigation, etc.).
                # Re-raise as a clean disconnect so Starlette returns 499/closes
                # the socket without dumping the full traceback to the log.
                logger.info(
                    "middleware.camel_case.client_disconnect",
                    path=request.url.path,
                )
                raise

            if body:
                try:
                    data = json.loads(body)
                    converted = self._convert_keys_to_snake(data)
                    new_body = json.dumps(converted).encode()

                    async def receive():
                        return {"type": "http.request", "body": new_body, "more_body": False}

                    request._receive = receive
                except json.JSONDecodeError as exc:
                    logger.debug(
                        "middleware.camel_case.invalid_json",
                        error=str(exc),
                        path=request.url.path,
                    )
                except Exception as exc:  # noqa: BLE001 — fail open, never block the request
                    logger.warning(
                        "middleware.camel_case.conversion_failed",
                        error=str(exc),
                        error_type=type(exc).__name__,
                        path=request.url.path,
                    )

        return await call_next(request)

    def _convert_keys_to_snake(self, data: Any) -> Any:
        """
        Recursively convert all dictionary keys from camelCase to snake_case.
        """
        if isinstance(data, dict):
            return {self._camel_to_snake(key): self._convert_keys_to_snake(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._convert_keys_to_snake(item) for item in data]
        return data

    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase string to snake_case."""
        result = []
        for i, char in enumerate(name):
            if char.isupper():
                if i > 0 and (
                    # Previous char is lowercase
                    name[i - 1].islower()
                    or
                    # Next char exists and is lowercase (for acronyms)
                    (i < len(name) - 1 and name[i + 1].islower())
                ):
                    result.append("_")
                result.append(char.lower())
            else:
                result.append(char)
        return "".join(result)
