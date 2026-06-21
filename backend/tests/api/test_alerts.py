"""E2E — ``/me/alerts`` prefs (12-api §"Alertas", plan §8).

Requires the running stack (docker). Asserts the default shape, the PUT upsert,
and camelCase keys.
"""

import pytest
import requests
from expects import be_none, equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK
from tests.api.conftest import BASE_URL
from tests.api.conftest_owliver import auth_headers

pytestmark = [pytest.mark.api]


def test_get_alerts_default_shape(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.get(url=f"{BASE_URL}/v1/me/alerts", headers=headers, timeout=30)
    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data).to(have_key("emailEnabled"))
    expect(data).to(have_key("slackWebhookUrl"))


def test_put_alerts_upserts(login_user, api_key_header):
    headers = auth_headers(login_user.access_token, api_key_header)
    response = requests.put(
        url=f"{BASE_URL}/v1/me/alerts",
        json={"emailEnabled": False, "slackWebhookUrl": "https://hooks.example/x"},
        headers=headers,
        timeout=30,
    )
    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data["emailEnabled"]).to(equal(False))
    expect(data["slackWebhookUrl"]).to(equal("https://hooks.example/x"))

    # Re-read reflects the upsert.
    again = requests.get(url=f"{BASE_URL}/v1/me/alerts", headers=headers, timeout=30)
    expect(again.json()["data"]["emailEnabled"]).to(equal(False))
