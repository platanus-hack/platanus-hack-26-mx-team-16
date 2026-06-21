import os
from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
import requests
from requests import Response

from src.common.application.logging import get_logger
from src.common.domain.constants.status import HTTP_200_OK, HTTP_201_CREATED
from src.common.settings import settings

logger = get_logger()

BASE_URL = os.environ.get("E2E_BASE_URL", "http://api:8200")
USER_EMAIL = "user@test.com"
USER_PASSWORD = "pass1234567890"
TENANT_NAME = "tenant-test"


@pytest.fixture(scope="session")
def api_key_header() -> dict:
    """Provides the admin API key header, fetching from env var or using a default test key."""
    admin_api_key = os.environ.get("ADMIN_API_KEY", "test-super-secret-key")
    return {"x-api-key": admin_api_key}


# The E2E suite hits the live API container, which uses its own database
# (POSTGRES_DB defaults to ``postgres``) — NOT the ``doxiq_test`` DB the root
# conftest points the in-process engines at. We therefore build a dedicated URL
# against the API's DB for the isolation fixtures below.
_API_DB_NAME = os.environ.get("POSTGRES_DB", "postgres")
_API_DB_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{_API_DB_NAME}"
)


@pytest.fixture(autouse=True)
async def _reset_scan_rate_limit():
    """Clear the per-user scan rate-limit counters before every API test.

    ``POST /v1/scans`` is rate-limited 5/3600 per user via the Redis-backed
    ``RateLimiter`` (fixed_window), whose state persists across the whole test
    session. Without this reset the shared test user exhausts its 5-scan budget
    after a handful of tests and every later ``POST /scans`` returns 429,
    cascading into unrelated failures. We delete only the scan limiter keys
    (``rate_limit:fixed:scans:*``) so each test starts from a clean window; the
    limit itself is never weakened.
    """
    from redis.asyncio import Redis

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async for key in redis.scan_iter(match="rate_limit:fixed:scans:*"):
            await redis.delete(key)
    finally:
        await redis.aclose()
    yield


@pytest.fixture(autouse=True)
async def _reset_scan_fixtures():
    """Purge the synthetic ``*.example.com`` scan data before every API test.

    Scans are idempotent: ``POST /v1/scans`` returns the *existing* live scan
    (200) for an already-active ``(site, level)`` instead of creating a new one
    (201). Scan rows persist across runs (and stay ``queued`` because no worker
    advances them in this phase), so on the 2nd run the "first POST → 201" tests
    would see a stale live scan and get 200. Deleting the test ``sites`` (whose
    hostnames are all under ``example.com``) cascades — via the
    ``ondelete=CASCADE`` FKs — to their scans, findings, public_reports and
    scan_events, giving every test a clean slate. Only synthetic test hostnames
    are touched; real data is never affected.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(_API_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM sites WHERE hostname LIKE :pattern"),
                {"pattern": "%example.com"},
            )
    finally:
        await engine.dispose()
    yield


@dataclass
class LoginTestContext:
    access_token: str
    refresh_token: str
    tenant_slug: str | None = None
    tenant_id: str | None = None
    branch_ids: list = field(default_factory=list)
    pos_ids: list = field(default_factory=list)
    tenant_user_ids: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "LoginTestContext":
        tenant = data.get("tenant") or {}

        return cls(
            access_token=data["session"]["accessToken"],
            refresh_token=data["session"]["refreshToken"],
            tenant_slug=tenant.get("slug", None),
            tenant_id=tenant.get("uuid", None),
        )


def _login_user() -> Response:
    return requests.post(
        url=f"{BASE_URL}/v1/auth/login/",
        json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
        },
        timeout=30,
    )


def _db_cleanup(tenant_id: str, branch_ids: list, pos_ids: list, tenant_user_ids: list, api_key_header: dict):
    # Best-effort teardown. ``/v1/tests/cleanup`` is a test-support endpoint that
    # is not (yet) mounted in Owliver — when it is absent the API returns 404.
    # Teardown must never hard-fail the whole API test session over a missing
    # cleanup hook, so we log and move on instead of asserting 200.
    response = requests.delete(
        url=f"{BASE_URL}/v1/tests/cleanup",
        json={
            "tenantId": tenant_id,
            "branchIds": branch_ids,
            "posIds": pos_ids,
            "tenantUserIds": tenant_user_ids,
        },
        headers=api_key_header,
        timeout=30,
    )
    if response.status_code != HTTP_200_OK:
        logger.warning("Cleanup endpoint unavailable; skipping", status_code=response.status_code)
        return
    logger.info("Cleanup registered tenant")
    logger.info("Cleanup registered tenant_user")


@pytest.fixture(scope="session")
def new_registered_user(api_key_header: dict) -> bool:
    response = requests.post(
        url=f"{BASE_URL}/v1/users",
        json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
        },
        headers=api_key_header,
        timeout=30,
    )
    if response.status_code != HTTP_201_CREATED:
        logger.info("User already exists", email=USER_EMAIL)
        return False
    logger.info("New user registered", email=USER_EMAIL)
    return True


@pytest.fixture(scope="session")
def new_registered_tenant(new_registered_user, api_key_header: dict):
    response = _login_user()
    if response.status_code != HTTP_201_CREATED:
        logger.error("Login failed", status_code=response.status_code, response_text=response.text)
        pytest.fail(f"Login failed: {response.status_code} - {response.text}")

    login_user = LoginTestContext.from_dict(response.json()["data"])

    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
    }
    headers.update(api_key_header)
    tenant_response = requests.post(
        url=f"{BASE_URL}/v1/tenants",
        json={
            "name": TENANT_NAME,
            "countryCode": "BO",
        },
        headers=headers,
        timeout=30,
    )
    if tenant_response.status_code != HTTP_201_CREATED:
        logger.warning("Tenant creation status", status_code=tenant_response.status_code)
    logger.info("New Tenant registered", tenant_name=TENANT_NAME)


@pytest.fixture(scope="session")
def login_user(new_registered_user, new_registered_tenant, api_key_header: dict) -> Generator[LoginTestContext]:
    response = _login_user()
    assert response.status_code == HTTP_201_CREATED
    user_login = LoginTestContext.from_dict(response.json()["data"])

    yield user_login

    _db_cleanup(
        tenant_id=user_login.tenant_id,
        branch_ids=user_login.branch_ids,
        pos_ids=user_login.pos_ids,
        tenant_user_ids=user_login.tenant_user_ids,
        api_key_header=api_key_header,
    )
