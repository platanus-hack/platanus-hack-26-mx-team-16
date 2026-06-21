"""E2E — ``GET /scans/{id}/stream`` SSE live view (10 §3–§4, plan §8.1).

Requires the running stack (docker: api + postgres + redis). Asserts the auth gate
(private scan: 404 anon / 200 owner), the SSE content-type + anti-buffer headers,
and that the stream opens with a ``ready`` frame (replay-then-tail entry point).
"""

import uuid

import pytest
import requests
from expects import contain, equal, expect, start_with

from src.common.domain.constants.status import HTTP_404_NOT_FOUND
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def _create_private_scan(headers) -> str:
    created = requests.post(
        url=f"{BASE_URL}/v1/scans",
        json={"url": "https://stream-e2e.example.com", "level": "intermedio", "authorized": True},
        headers=headers,
        timeout=30,
    )
    expect(created.status_code).to(equal(201))
    return created.json()["data"]["scanId"]


def test_unknown_scan_stream_returns_404(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.get(
        url=f"{BASE_URL}/v1/scans/{uuid.uuid4()}/stream",
        headers=headers,
        timeout=30,
    )
    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))


def test_private_scan_stream_without_auth_is_404_not_403(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    scan_id = _create_private_scan(headers)

    anon = requests.get(
        url=f"{BASE_URL}/v1/scans/{scan_id}/stream",
        headers=api_key_header,  # admin api key only, NO Bearer
        timeout=30,
    )
    expect(anon.status_code).to(equal(HTTP_404_NOT_FOUND))


def test_private_scan_stream_with_owner_opens_with_ready_frame(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    scan_id = _create_private_scan(headers)

    with requests.get(
        url=f"{BASE_URL}/v1/scans/{scan_id}/stream",
        headers=headers,
        stream=True,
        timeout=30,
    ) as response:
        expect(response.status_code).to(equal(200))
        expect(response.headers["content-type"]).to(start_with("text/event-stream"))
        expect(response.headers.get("cache-control", "")).to(contain("no-transform"))

        # The first SSE frame is always ``ready`` (replay-then-tail opener).
        # Bind ONE line iterator: ``requests`` loses buffered position if you call
        # ``iter_lines()`` afresh per ``next()`` (the new generator can hit EOF on
        # a half-consumed stream), so read all lines from a single iterator.
        line_iter = response.iter_lines(decode_unicode=True, chunk_size=1)
        # Read a few lines to find the event name robustly.
        lines = []
        for _ in range(5):
            line = next(line_iter)
            lines.append(line)
        joined = "\n".join(l for l in lines if l is not None)
        expect(joined).to(contain("ready"))
