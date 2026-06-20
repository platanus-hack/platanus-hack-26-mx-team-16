import pytest
import requests
from expects import equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED
from tests.api.conftest import BASE_URL, LoginTestContext

pytestmark = [pytest.mark.api]


def test_refresh__returns_new_tokens(login_user: LoginTestContext):
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/refresh",
        json={"refreshToken": login_user.refresh_token},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data).to(have_key("session"))
    expect(data["session"]).to(have_key("accessToken"))
    expect(data["session"]).to(have_key("refreshToken"))


def test_refresh__invalid_token_returns_401():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/refresh",
        json={"refreshToken": "invalid.token.here"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_401_UNAUTHORIZED))


def test_refresh__empty_token_returns_401():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/refresh",
        json={"refreshToken": ""},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_401_UNAUTHORIZED))
