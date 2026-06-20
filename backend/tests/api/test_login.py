import pytest
import requests
from expects import be_a, contain, equal, expect, have_key

from src.common.domain.constants.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from tests.api.conftest import BASE_URL, USER_EMAIL, USER_PASSWORD, LoginTestContext

pytestmark = [pytest.mark.api]


def test_login__returns_session(login_user: LoginTestContext):
    expect(login_user).to(be_a(LoginTestContext))
    expect(login_user.access_token).to(be_a(str))
    expect(login_user.refresh_token).to(be_a(str))
    expect(login_user.tenant_slug).to(be_a(str))
    expect(login_user.tenant_id).to(be_a(str))


def test_login__response_has_expected_structure(login_user: LoginTestContext):
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_201_CREATED))
    data = response.json()["data"]
    expect(data).to(have_key("session"))
    expect(data).to(have_key("user"))
    expect(data).to(have_key("tenant"))
    expect(data).to(have_key("tenantRole"))
    expect(data["session"]).to(have_key("accessToken"))
    expect(data["session"]).to(have_key("refreshToken"))


def test_login__wrong_password():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"email": USER_EMAIL, "password": "wrongpassword"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_401_UNAUTHORIZED))


def test_login__nonexistent_email():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))


def test_login__missing_fields_returns_422():
    response = requests.post(
        url=f"{BASE_URL}/v1/auth/login",
        json={"password": "password"},
        timeout=30,
    )

    expect(response.status_code).to(equal(422))
