"""Reusable secret/token primitives (F0 groundwork).

Several features mint a secret that is **shown once** and then stored opaquely:

- ``whsec_`` — outbound webhook HMAC signing key (``signing.py``); the bytes
  after the prefix are base64 so receivers can reuse Svix client libraries.
- ``dxk_``  — tenant-scoped M2M API key (F9 ``TenantApiKey``); stored **hashed**,
  compared on every request, never revealed again after creation.
- ``src_``  — routable Source ingest token (F8 ``workflow_sources.route_token``);
  stored raw in a dedicated unique column and resolved on ``POST /v1/ingest``.

This module centralises generation, hashing and the "shown once" discipline so
each consumer does not re-implement it. Presenters expose only :func:`has_secret`;
the cleartext leaves the system exactly once via :meth:`RevealableSecret.reveal`.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

# Prefixes — kept here so every feature uses the same vocabulary.
SECRET_PREFIX_HMAC = "whsec_"  # outbound webhook signing key
SECRET_PREFIX_API_KEY = "dxk_"  # tenant M2M api key
SECRET_PREFIX_ROUTE_TOKEN = "src_"  # source ingest route token

_DEFAULT_BYTES = 32


def generate_base64_secret(prefix: str, *, n_bytes: int = _DEFAULT_BYTES) -> str:
    """``<prefix><standard-base64(n random bytes)>`` — for HMAC keys.

    Standard base64 (not url-safe) so the token after the prefix decodes back to
    the raw HMAC key (Svix-strict, see ``signing.py``).
    """
    return f"{prefix}{base64.b64encode(secrets.token_bytes(n_bytes)).decode('ascii')}"


def generate_url_safe_token(prefix: str, *, n_bytes: int = _DEFAULT_BYTES) -> str:
    """``<prefix><url-safe-base64(n random bytes)>`` — for api keys / route tokens.

    URL-safe so the token is safe inside a path segment (``/v1/ingest/{token}``)
    and an ``X-Api-Key`` header without escaping.
    """
    return f"{prefix}{secrets.token_urlsafe(n_bytes)}"


def hash_token(value: str) -> str:
    """SHA-256 hex digest — at-rest storage for tokens that are *compared*, not
    revealed (api keys). Constant-time comparison via :func:`verify_token`."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_token(value: str, hashed: str) -> bool:
    """Constant-time check of a presented token against its stored hash."""
    return secrets.compare_digest(hash_token(value), hashed)


def has_secret(value: str | None) -> bool:
    """Presenter helper — whether a secret is set, without revealing it."""
    return value is not None


@dataclass(frozen=True)
class RevealableSecret:
    """A secret shown once at mint time, then stored opaquely.

    ``value`` is the full prefixed token. Build one with :meth:`generate`, return
    it once through :meth:`reveal`, and persist either the raw value (HMAC / route
    token) or :attr:`hashed` (api key). :meth:`regenerate` rotates it.
    """

    value: str

    @classmethod
    def generate(cls, prefix: str, *, n_bytes: int = _DEFAULT_BYTES, url_safe: bool = False) -> RevealableSecret:
        token = (
            generate_url_safe_token(prefix, n_bytes=n_bytes)
            if url_safe
            else generate_base64_secret(prefix, n_bytes=n_bytes)
        )
        return cls(token)

    def regenerate(self, *, url_safe: bool = False) -> RevealableSecret:
        prefix, _, _ = self.value.partition("_")
        return self.generate(f"{prefix}_", url_safe=url_safe)

    def reveal(self) -> str:
        return self.value

    @property
    def hashed(self) -> str:
        return hash_token(self.value)
