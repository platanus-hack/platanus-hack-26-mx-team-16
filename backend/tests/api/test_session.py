import pytest
import requests
from expects import equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from tests.api.conftest import BASE_URL, USER_EMAIL, USER_PASSWORD

pytestmark = [pytest.mark.api]


def _login():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
        timeout=30,
    )
    return response.json()["data"]


def test_session__returns_user_profile():
    data = _login()
    access_token = data["session"]["accessToken"]

    response = requests.get(
        url=f"{BASE_URL}/v1/auth/session",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
    result = response.json()["data"]
    expect(result).to(have_key("user"))
    expect(result).to(have_key("tenant"))
    expect(result).to(have_key("tenantRole"))
    expect(result["user"]).to(have_key("uuid"))
    expect(result["user"]).to(have_key("emailAddress"))


def test_session__unauthenticated_returns_403():
    response = requests.get(
        url=f"{BASE_URL}/v1/auth/session",
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_403_FORBIDDEN))


def test_session__invalid_token_returns_401():
    response = requests.get(
        url=f"{BASE_URL}/v1/auth/session",
        headers={"Authorization": "Bearer invalid.token.here"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_401_UNAUTHORIZED))
