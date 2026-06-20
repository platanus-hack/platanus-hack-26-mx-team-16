from src.common.database.models.tenant_api_key import TenantApiKeyORM
from src.common.domain.models.tenant_api_key import TenantApiKey


def build_tenant_api_key(orm: TenantApiKeyORM) -> TenantApiKey:
    return TenantApiKey(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        name=orm.name,
        prefix=orm.prefix,
        key_hash=orm.key_hash,
        enabled=orm.enabled,
        last_used_at=orm.last_used_at,
        expires_at=orm.expires_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
