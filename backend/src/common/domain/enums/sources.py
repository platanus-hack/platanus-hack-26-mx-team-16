"""Enums for configurable ingest Sources (F8 · D3 · D6)."""

from src.common.domain.enums.base_enum import BaseEnum


class SourceAuthMode(BaseEnum):
    """How an inbound ``POST /v1/ingest/{token}`` proves it is allowed (D3).

    ``API_KEY`` (the default, D6): an ``X-Api-Key: dxk_…`` header, compared
    against the stored hash. ``HMAC``: a signature over the body + a timestamp
    (anti-replay), verified against the stored signing secret."""

    API_KEY = "api_key"
    HMAC = "hmac"
