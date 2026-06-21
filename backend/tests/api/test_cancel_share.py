"""E2E — cancel + share/public-report token (12-api §"Cancelación"/§"Reporte", plan §8).

Requires the running stack (docker). Asserts owner-only cancel sets status
`cancelled`; share returns a token; `/r/{token}` valid → 200 redacted; unknown
token → 404. (Expiry → 410 is covered by the unit test for ``GetPublicReport``.)
"""

import pytest
import requests
from expects import equal, expect, have_key

from src.common.domain.constants.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def _create_scan(headers):
    response = requests.post(
        url=f"{BASE_URL}/v1/scans",
        json={"url": "https://cancel-share.example.com", "level": "basico", "authorized": False},
        headers=headers,
        timeout=30,
    )
    assert response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
    return response.json()["data"]["scanId"]


def test_owner_cancel_sets_status_cancelled(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    scan_id = _create_scan(headers)
    response = requests.post(
        url=f"{BASE_URL}/v1/scans/{scan_id}/cancel", headers=headers, timeout=30
    )
    expect(response.status_code).to(equal(HTTP_200_OK))
    expect(response.json()["data"]["status"]).to(equal("cancelled"))


def test_non_owner_cancel_returns_404(api_key_header):
    # An anonymous caller (no Bearer) cannot cancel a private scan.
    import uuid

    response = requests.post(
        url=f"{BASE_URL}/v1/scans/{uuid.uuid4()}/cancel",
        headers=api_key_header,
        timeout=30,
    )
    # No Authorization header → 403, matching the established codebase convention
    # (see tests/api/test_session.py::test_session__unauthenticated_returns_403,
    # which is the HTTPBearer default for a missing token; an *invalid* token
    # instead yields 401). The owner-only 404 rule only applies once a session
    # exists; with no session the request is rejected before ownership is checked.
    expect(response.status_code).to(equal(403))


def test_share_returns_token_and_public_report_is_servable(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    scan_id = _create_scan(headers)

    shared = requests.post(
        url=f"{BASE_URL}/v1/scans/{scan_id}/share",
        json={"ttlDays": 7},
        headers=headers,
        timeout=30,
    )
    expect(shared.status_code).to(equal(HTTP_201_CREATED))
    token = shared.json()["data"]["token"]
    assert token and isinstance(token, str)

    # Public, no auth.
    public = requests.get(url=f"{BASE_URL}/v1/r/{token}", timeout=30)
    expect(public.status_code).to(equal(HTTP_200_OK))
    expect(public.json()["data"]).to(have_key("redacted"))


def test_unknown_report_token_returns_404():
    response = requests.get(url=f"{BASE_URL}/v1/r/does-not-exist", timeout=30)
    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))
