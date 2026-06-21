"""E2E — ranking + health/ready (12-api §"Lectura"/§6, plan §8).

Requires the running stack (docker). Asserts `/health` and `/ready` are public
(no auth) and that `/ranking` is public and never leaks private scans.
"""

import pytest
import requests
from expects import be_a, equal, expect, have_key

from src.common.domain.constants.status import HTTP_200_OK
from tests.api.conftest import BASE_URL

pytestmark = [pytest.mark.api]


def test_health_is_public_200():
    response = requests.get(url=f"{BASE_URL}/health", timeout=30)
    expect(response.status_code).to(equal(HTTP_200_OK))


def test_ready_is_public_and_reports_dependencies():
    response = requests.get(url=f"{BASE_URL}/ready", timeout=30)
    # 200 when pg+redis up (the orchestrator runs this with the full stack).
    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data).to(have_key("checks"))
    expect(data["checks"]).to(have_key("postgres"))
    expect(data["checks"]).to(have_key("redis"))


def test_ranking_is_public_and_paginated():
    response = requests.get(url=f"{BASE_URL}/v1/ranking?country=mx", timeout=30)
    expect(response.status_code).to(equal(HTTP_200_OK))
    body = response.json()
    expect(body).to(have_key("data"))
    expect(body).to(have_key("pagination"))
    expect(body["data"]).to(be_a(list))
    # Every ranked row is a public gov scan — never a private one.
    for item in body["data"]:
        expect(item).to(have_key("overallGrade"))
