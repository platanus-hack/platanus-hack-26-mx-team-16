"""E2E — anti-IDOR on ``GET /scans/{id}`` (12-api §"AuthZ", plan §8).

Requires the running stack (docker). Asserts a private scan is 404 (not 403) to a
non-owner, and an unknown UUID is 404.
"""

import uuid

import pytest
import requests
from expects import equal, expect

from src.common.domain.constants.status import HTTP_404_NOT_FOUND
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def test_unknown_scan_uuid_returns_404(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.get(
        url=f"{BASE_URL}/v1/scans/{uuid.uuid4()}",
        headers=headers,
        timeout=30,
    )
    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))


def test_private_scan_of_another_user_returns_404_not_403(login_user, api_key_header):
    """A private scan owned by user A must be 404 (never 403) for user B.

    We create a private (active) scan as the logged-in user, then query it with
    NO Authorization header (an unauthenticated/other caller). A private scan must
    not even confirm its existence → 404, never 200/403.
    """
    headers = auth_headers(login_user.access_token, api_key_header)
    created = requests.post(
        url=f"{BASE_URL}/v1/scans",
        json={"url": "https://idor-private.example.com", "level": "intermedio", "authorized": True},
        headers=headers,
        timeout=30,
    )
    expect(created.status_code).to(equal(201))
    scan_id = created.json()["data"]["scanId"]

    # Same id, but as an anonymous caller (only the admin api key, no Bearer).
    anon = requests.get(
        url=f"{BASE_URL}/v1/scans/{scan_id}",
        headers=api_key_header,
        timeout=30,
    )
    expect(anon.status_code).to(equal(HTTP_404_NOT_FOUND))
