"""E2E — watchlist CRUD + monitor toggle (12-api §"Watchlist", plan §8).

Requires the running stack (docker). Asserts POST returns a row with `id`, PATCH
toggles `monitor`, DELETE uses the watchlist-row id (not site_id), and a foreign
`{id}` → 404.
"""

import uuid

import pytest
import requests
from expects import be_false, be_true, contain, equal, expect, have_key

from src.common.domain.constants.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def test_watchlist_crud_and_toggle(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)

    # POST → 201 with a row id
    created = requests.post(
        url=f"{BASE_URL}/v1/watchlist",
        json={"url": "https://watch-me.example.com", "monitor": True},
        headers=headers,
        timeout=30,
    )
    expect(created.status_code).to(equal(HTTP_201_CREATED))
    row = created.json()["data"]
    expect(row).to(have_key("id"))
    expect(row["monitor"]).to(be_true)
    row_id = row["id"]

    # GET list contains it
    listed = requests.get(url=f"{BASE_URL}/v1/watchlist", headers=headers, timeout=30)
    expect(listed.status_code).to(equal(HTTP_200_OK))
    ids = [item["id"] for item in listed.json()["data"]]
    expect(ids).to(contain(row_id))

    # PATCH toggles monitor off
    patched = requests.patch(
        url=f"{BASE_URL}/v1/watchlist/{row_id}",
        json={"monitor": False},
        headers=headers,
        timeout=30,
    )
    expect(patched.status_code).to(equal(HTTP_200_OK))
    expect(patched.json()["data"]["monitor"]).to(be_false)

    # DELETE by row id
    deleted = requests.delete(
        url=f"{BASE_URL}/v1/watchlist/{row_id}", headers=headers, timeout=30
    )
    expect(deleted.status_code).to(equal(HTTP_200_OK))


def test_foreign_watchlist_id_returns_404(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.delete(
        url=f"{BASE_URL}/v1/watchlist/{uuid.uuid4()}", headers=headers, timeout=30
    )
    expect(response.status_code).to(equal(HTTP_404_NOT_FOUND))
