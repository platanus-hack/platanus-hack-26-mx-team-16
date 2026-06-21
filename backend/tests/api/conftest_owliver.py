"""Shared helpers for the Owliver scan/site E2E tests (12-api §8).

These run against the real stack (docker: api + postgres + redis) — unreachable
from the dev host; the orchestrator runs them under `make test_api`. They reuse
the boilerplate ``login_user`` fixture (Bearer access token) and the admin
``api_key_header`` from ``tests/api/conftest.py``.
"""

from __future__ import annotations

from tests.api.conftest import BASE_URL


def auth_headers(access_token: str, api_key_header: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    headers.update(api_key_header)
    return headers


__all__ = ["BASE_URL", "auth_headers"]
