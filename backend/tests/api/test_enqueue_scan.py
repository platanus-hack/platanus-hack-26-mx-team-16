"""E2E — ``POST /scans`` contract (12-api §2, plan §8).

Requires the running stack (docker) — run via `make test_api`. Asserts:
- active level without `authorized` → 422 `attestation_required`
- basic valid → 201 + `scanId`
- second POST of the same live (site, level) → 200 with the same `scanId` (idempotency)
- exceeding 5 scans/hour → 429 + `Retry-After`
"""

import requests
from expects import contain, equal, expect, have_key

import pytest

from src.common.domain.constants.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def _post_scan(headers, url, level, authorized):
    return requests.post(
        url=f"{BASE_URL}/v1/scans",
        json={"url": url, "level": level, "authorized": authorized},
        headers=headers,
        timeout=30,
    )


def test_active_without_attestation_returns_422(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = _post_scan(headers, "https://attest-422.example.com", "intermedio", False)
    expect(response.status_code).to(equal(422))
    body = response.json()
    expect(body).to(have_key("errors"))
    expect(body["errors"][0]["code"]).to(equal("attestation_required"))


def test_basic_valid_returns_201_with_scan_id(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = _post_scan(headers, "https://basic-201.example.com", "basico", False)
    expect(response.status_code).to(equal(HTTP_201_CREATED))
    data = response.json()["data"]
    expect(data).to(have_key("scanId"))
    expect(data["status"]).to(equal("queued"))


def test_idempotent_second_post_returns_200_same_scan(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    url = "https://idempotent.example.com"
    first = _post_scan(headers, url, "basico", False)
    expect(first.status_code).to(equal(HTTP_201_CREATED))
    first_id = first.json()["data"]["scanId"]

    second = _post_scan(headers, url, "basico", False)
    expect(second.status_code).to(equal(HTTP_200_OK))
    expect(second.json()["data"]["scanId"]).to(equal(first_id))


def test_rate_limit_returns_429_with_retry_after(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    # 5/hour per user. Fire enough distinct domains to cross the limit.
    statuses = []
    for i in range(7):
        r = _post_scan(headers, f"https://rl-{i}.example.com", "basico", False)
        statuses.append(r.status_code)
        if r.status_code == 429:
            expect(r.headers).to(have_key("Retry-After"))
            break
    expect(statuses).to(contain(429))
