"""``POST /scans`` — idempotent, attested, rate-limited scan enqueue (12-api §2, §3).

Response codes (spec §"Códigos de respuesta"):
- 201 new scan queued (body: ``scanId`` + state)
- 200 idempotent hit on a live ``(site, level)`` (body: the existing ``scanId``)
- 422 active level without ``authorized=true`` (``attestation_required``), via the
  01-legal gate inside ``EnqueueScan`` — handled by the global ``DomainError`` handler
- 429 rate-limit (5/h per user) with ``Retry-After`` — via the existing Redis
  ``RateLimiter`` + ``rate_limit_exception_handler``

Rate-limit: the foundation's ``create_rate_limit_dependency`` keys off the sync
``Request`` only, so we key per **user** with a small async dependency that runs
the same ``RateLimiter`` after auth resolves the user. ``API_SCAN_RATE_LIMIT`` =
(5, 3600) from 01-legal.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, status

from src.common.domain.legal.constants import API_SCAN_RATE_LIMIT
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import (
    BusContextDep,
    DomainContextDep,
    RedisClientDep,
)
from src.common.infrastructure.dependencies.session import (
    get_optional_authenticated_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.infrastructure.services.rate_limiter import (
    RateLimiter,
    RateLimitExceededError,
)
from src.scans.application.use_cases.enqueue_scan import EnqueueScan
from src.scans.presentation.presenters.scan import ScanCreatedPresenter
from src.scans.presentation.requests.enqueue_scan import EnqueueScanRequest

_SCAN_LIMIT, _SCAN_WINDOW = API_SCAN_RATE_LIMIT


async def _enforce_scan_rate_limit(
    request: Request,
    redis_client: RedisClientDep,
    user: Annotated[User | None, Depends(get_optional_authenticated_user)],
) -> User | None:
    """Per-requester fixed-window limit on ``POST /scans`` (5/h). The public
    ``/scan`` page enqueues anonymously (12-api lists ``POST /scans`` without the
    ``(auth)`` marker), so auth is optional: authenticated callers are keyed by
    user id, anonymous callers by client IP. Raises ``RateLimitExceededError``
    (→ 429 + Retry-After) when exceeded."""
    if user is not None:
        bucket = f"scans:{user.uuid}"
    else:
        client_ip = request.client.host if request.client else "unknown"
        bucket = f"scans:ip:{client_ip}"
    rate_limiter = RateLimiter(redis_client=redis_client)
    try:
        _, remaining, _ = await rate_limiter.check_rate_limit(
            key=bucket,
            limit=_SCAN_LIMIT,
            window=_SCAN_WINDOW,
            strategy="fixed_window",
        )
        request.state.rate_limit_limit = _SCAN_LIMIT
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_window = _SCAN_WINDOW
    except RateLimitExceededError as exc:
        request.state.rate_limit_limit = exc.limit
        request.state.rate_limit_remaining = 0
        request.state.rate_limit_retry_after = exc.retry_after
        raise
    return user


async def enqueue_scan(
    request: EnqueueScanRequest,
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
    user: Annotated[User | None, Depends(_enforce_scan_rate_limit)],
) -> ApiJSONResponse:
    result = await EnqueueScan(
        url=request.url,
        level=request.level,
        authorized=request.authorized,
        user=user,
        site_repository=domain_context.site_repository,
        scan_repository=domain_context.scan_repository,
        command_bus=bus_context.command_bus,
    ).execute()

    status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return ApiJSONResponse(
        content=ScanCreatedPresenter(result.scan).to_dict,
        status_code=status_code,
    )
