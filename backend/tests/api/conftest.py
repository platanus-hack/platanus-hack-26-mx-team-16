import os
from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
import requests
from requests import Response

from src.common.application.logging import get_logger
from src.common.domain.constants.status import HTTP_200_OK, HTTP_201_CREATED

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
    assert response.status_code == HTTP_200_OK
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
