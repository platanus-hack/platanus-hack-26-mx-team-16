"""F9 · M4: mint + resolve tenant M2M API keys."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from expects import be_none, equal, expect

from src.common.application.helpers.secrets import SECRET_PREFIX_API_KEY, hash_token
from src.common.domain.models.tenant_api_key import TenantApiKey
from src.tenants.application.api_keys.service import (
    MintTenantApiKey,
    resolve_tenant_api_key,
)

_TENANT = uuid4()
_NOW = datetime(2026, 6, 9, tzinfo=timezone.utc)


class _FakeRepo:
    def __init__(self):
        self.by_hash: dict[str, TenantApiKey] = {}

    async def create(self, key: TenantApiKey) -> TenantApiKey:
        self.by_hash[key.key_hash] = key
        return key

    async def find_by_hash(self, key_hash: str) -> TenantApiKey | None:
        return self.by_hash.get(key_hash)


async def test_mint__returns_dxk_plaintext_once_and_stores_only_hash():
    repo = _FakeRepo()

    minted = await MintTenantApiKey(tenant_id=_TENANT, name="ci", repository=repo).execute()

    expect(minted.plaintext.startswith(SECRET_PREFIX_API_KEY)).to(equal(True))
    expect(minted.key.key_hash).to(equal(hash_token(minted.plaintext)))
    expect(minted.key.tenant_id).to(equal(_TENANT))


async def test_resolve__valid_key_returns_tenant_binding():
    repo = _FakeRepo()
    minted = await MintTenantApiKey(tenant_id=_TENANT, name="ci", repository=repo).execute()

    resolved = await resolve_tenant_api_key(minted.plaintext, repo, now=_NOW)

    expect(resolved.tenant_id).to(equal(_TENANT))


async def test_resolve__rejects_unknown_disabled_and_expired():
    repo = _FakeRepo()
    minted = await MintTenantApiKey(tenant_id=_TENANT, name="ci", repository=repo).execute()

    expect(await resolve_tenant_api_key("dxk_unknown", repo, now=_NOW)).to(be_none)
    expect(await resolve_tenant_api_key(None, repo, now=_NOW)).to(be_none)

    minted.key.enabled = False
    expect(await resolve_tenant_api_key(minted.plaintext, repo, now=_NOW)).to(be_none)

    minted.key.enabled = True
    minted.key.expires_at = _NOW - timedelta(days=1)
    expect(await resolve_tenant_api_key(minted.plaintext, repo, now=_NOW)).to(be_none)
