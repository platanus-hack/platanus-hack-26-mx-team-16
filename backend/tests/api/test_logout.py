import pytest
import requests
from expects import equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED
from tests.api.conftest import BASE_URL, USER_EMAIL, USER_PASSWORD

pytestmark = [pytest.mark.api]


def _login():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
        timeout=30,
    )
    return response.json()["data"]


def test_logout__returns_success():
    data = _login()
    refresh_token = data["session"]["refreshToken"]

    response = requests.post(
        url=f"{BASE_URL}/v1/auth/logout",
        json={"refreshToken": refresh_token},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
    expect(response.json()["data"]).to(have_key("status"))
    expect(response.json()["data"]["status"]).to(equal("SUCCESS"))


def test_logout__empty_token_returns_error():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/logout",
        json={"refreshToken": ""},
        timeout=30,
    )

    # Empty refresh token cannot be decoded
    expect(response.status_code).not_to(equal(HTTP_200_OK))
