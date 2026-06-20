from src.common.database.models.connection_account import ConnectionAccountORM
from src.connections.domain.models.connection_account import ConnectionAccount


def build_connection_account(orm_instance: ConnectionAccountORM) -> ConnectionAccount:
    """Map a ``ConnectionAccountORM`` row to the domain model.

    ``provider`` / ``status`` / ``capabilities`` are stored as strings and
    coerced to their enums by Pydantic on construction.
    """
    return ConnectionAccount(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        provider=orm_instance.provider,
        display_name=orm_instance.display_name,
        capabilities=orm_instance.capabilities,
        status=orm_instance.status,
        config=orm_instance.config,
        secret=orm_instance.secret,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
