import functools
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import httpx

from src.common.application.helpers.code_styles import underscoreize
from src.common.application.logging import get_logger

logger = get_logger(__name__)
from src.common.domain.entities.common.error_feedback import ErrorFeedback

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])

HTTP_400_BAD_REQUEST = 400
HTTP_500_SERVER_ERROR = 500


def catch_httpx_exceptions(*, raw_response: bool = False) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                text = exc.response.text
                logger.info(
                    "http.error.status",
                    status_code=status,
                    response_text=text,
                    url=str(exc.request.url),
                )

                if HTTP_400_BAD_REQUEST <= status < HTTP_500_SERVER_ERROR:
                    if raw_response:
                        return underscoreize(exc.response.json())
                    return ErrorFeedback(**underscoreize(exc.response.json()))
                raise
            except httpx.RequestError as exc:
                logger.info(
                    "http.error.request",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise

        return wrapper

    return decorator
