from src.common.database.models.workflow_source import WorkflowSourceORM
from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.enums.sources import SourceAuthMode
from src.connections.domain.models.workflow_source import WorkflowSource


def build_workflow_source(orm: WorkflowSourceORM) -> WorkflowSource:
    return WorkflowSource(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        workflow_id=orm.workflow_id,
        provider=ConnectionProvider(orm.provider),
        account_id=orm.account_id,
        route_token=orm.route_token,
        auth_mode=SourceAuthMode(orm.auth_mode),
        secret=orm.secret,
        config=orm.config,
        enabled=orm.enabled,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
