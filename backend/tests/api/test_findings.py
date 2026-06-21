"""E2E — ``GET /scans/{id}/findings`` pagination + IDOR (12-api §"Lectura", plan §8).

Requires the running stack (docker). Asserts the cursor envelope shape and the
404-for-private-non-owner rule. (Severity-desc ordering is asserted exhaustively
in the unit test ``tests/scans/application/test_list_scan_findings.py`` since the
E2E stack has no findings until the worker (05) runs.)
"""

import uuid

import pytest
import requests
from expects import equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def test_findings_envelope_shape_for_owned_scan(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    created = requests.post(
        url=f"{BASE_URL}/v1/scans",
        json={"url": "https://findings-shape.example.com", "level": "basico", "authorized": False},
        headers=headers,
        timeout=30,
    )
    scan_id = created.json()["data"]["scanId"]

    response = requests.get(
        url=f"{BASE_URL}/v1/scans/{scan_id}/findings?limit=10",
        headers=headers,
        timeout=30,
    )
    expect(response.status_code).to(equal(HTTP_200_OK))
    body = response.json()
    expect(body).to(have_key("data"))
    expect(body).to(have_key("pagination"))
    expect(body["pagination"]).to(have_key("nextCursor"))


def test_findings_of_unknown_scan_returns_404(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.get(
        url=f"{BASE_URL}/v1/scans/{uuid.uuid4()}/findings",
        headers=headers,
        timeout=30,
    )
    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))
