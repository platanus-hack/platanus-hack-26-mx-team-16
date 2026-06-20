from src.common.database.models.tool_definition import ToolDefinitionORM
from src.common.domain.enums.tools import ToolTransport
from src.workflows.domain.models.tool import ToolDefinition


def build_tool_definition(orm: ToolDefinitionORM) -> ToolDefinition:
    return ToolDefinition(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        workflow_id=orm.workflow_id,
        name=orm.name,
        display_name=orm.display_name,
        description=orm.description,
        transport=ToolTransport(orm.transport),
        connection_account_id=orm.connection_account_id,
        input_schema=orm.input_schema,
        output_schema=orm.output_schema,
        config=orm.config,
        enabled=orm.enabled,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
