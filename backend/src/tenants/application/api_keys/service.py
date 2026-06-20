"""Mint + resolve tenant M2M API keys (F9 · M4).

Mint generates a ``dxk_`` key, stores only its hash, and returns the cleartext
**once**. Resolution hashes a presented key and looks up its tenant binding,
honouring ``enabled``/``expires_at``. Both reuse the F0 secret primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.common.application.helpers.secrets import (
    SECRET_PREFIX_API_KEY,
    generate_url_safe_token,
    hash_token,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenant_api_key import TenantApiKey
from src.tenants.domain.repositories.tenant_api_key import TenantApiKeyRepository

_PREFIX_LEN = 12  # chars of the cleartext shown in the UI to identify a key


@dataclass
class MintedApiKey:
    key: TenantApiKey
    plaintext: str  # returned exactly once


@dataclass
class MintTenantApiKey(UseCase):
    tenant_id: UUID
    name: str
    repository: TenantApiKeyRepository
    expires_at: datetime | None = None

    async def execute(self) -> MintedApiKey:
        plaintext = generate_url_safe_token(SECRET_PREFIX_API_KEY)
        stored = await self.repository.create(
            TenantApiKey(
                uuid=uuid4(),
                tenant_id=self.tenant_id,
                name=self.name,
                prefix=plaintext[:_PREFIX_LEN],
                key_hash=hash_token(plaintext),
                expires_at=self.expires_at,
            )
        )
        return MintedApiKey(key=stored, plaintext=plaintext)


async def resolve_tenant_api_key(
    presented_key: str | None,
    repository: TenantApiKeyRepository,
    *,
    now: datetime | None = None,
) -> TenantApiKey | None:
    """Return the tenant-bound key for a presented ``dxk_`` value, or ``None``."""
    if not presented_key:
        return None
    key = await repository.find_by_hash(hash_token(presented_key))
    if key is None or not key.enabled:
        return None
    if key.expires_at is not None and now is not None and key.expires_at < now:
        return None
    return key
