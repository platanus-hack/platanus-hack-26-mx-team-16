"""Workflow-scoped Tool endpoints (F5, re-scoped 2026-06).

Tools son config 1:1 del workflow (mismo patrón que pipeline · ADR 0002); la
credencial vive en la ``ConnectionAccount`` org-level (capability ``LOOKUP``).
Las rutas cuelgan de ``/workflows/{workflow_id}/tools`` y el guard
``require_workflow_action("manage")`` se aplica en el router.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, status
from pydantic import BaseModel, Field

from src.common.domain.enums.connections import ConnectionCapability, ConnectionProvider
from src.common.domain.enums.tools import ToolTransport
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.connections.domain.exceptions import (
    ConnectionAccountNotFoundError,
    InvalidConnectionCapabilityError,
)
from src.connections.infrastructure.repositories.sql_connection_account import (
    SQLConnectionAccountRepository,
)
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.infrastructure.repositories.sql_tool import SQLToolRepository


class CreateToolRequest(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    transport: ToolTransport = ToolTransport.HTTP
    # phases-config · F5: opcional — las script tools (PYTHON/JS) no usan cuenta de
    # conexión. Para transport HTTP el endpoint la sigue exigiendo (LOOKUP).
    connection_account_id: UUID | None = None
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)


def _present(tool: ToolDefinition) -> dict:
    # E3: config/schemas are non-secret (the secret lives on the
    # ConnectionAccount) and the UI needs them to edit URL templates/schemas.
    return {
        "uuid": str(tool.uuid),
        "workflow_id": str(tool.workflow_id),
        "name": tool.name,
        "display_name": tool.display_name,
        "description": tool.description,
        "transport": tool.transport.value,
        "connection_account_id": (str(tool.connection_account_id) if tool.connection_account_id else None),
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
        "config": tool.config,
        "enabled": tool.enabled,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


async def create_workflow_tool(
    workflow_id: UUID,
    request: CreateToolRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    # phases-config · F5: las script tools (PYTHON/JS) corren en sandbox aislado y
    # no hacen HTTP ⇒ no requieren cuenta de conexión. Las HTTP siguen colgando de
    # una cuenta HTTP con capability LOOKUP (E3).
    is_script = request.transport in (ToolTransport.PYTHON, ToolTransport.JS)
    connection_account_id: UUID | None = None
    if is_script:
        # El código vive en `config` ({runtime, entrypoint, code, limits}); una
        # cuenta enviada por error se ignora (la script tool no la usa).
        connection_account_id = None
    else:
        if request.connection_account_id is None:
            # HTTP sin cuenta = capability LOOKUP no satisfecha.
            raise InvalidConnectionCapabilityError(ConnectionProvider.HTTP.value, ConnectionCapability.LOOKUP.value)
        account = await SQLConnectionAccountRepository(session).find_by_id(request.connection_account_id, tenant.uuid)
        if account is None:
            raise ConnectionAccountNotFoundError(str(request.connection_account_id))
        if account.provider != ConnectionProvider.HTTP or ConnectionCapability.LOOKUP not in account.capabilities:
            raise InvalidConnectionCapabilityError(account.provider.value, ConnectionCapability.LOOKUP.value)
        connection_account_id = request.connection_account_id
    tool = await SQLToolRepository(session).upsert(
        ToolDefinition(
            uuid=uuid4(),
            tenant_id=tenant.uuid,
            workflow_id=workflow_id,
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            transport=request.transport,
            connection_account_id=connection_account_id,
            input_schema=request.input_schema,
            output_schema=request.output_schema,
            config=request.config,
        )
    )
    return ApiJSONResponse(content=_present(tool), status_code=status.HTTP_201_CREATED)


async def list_workflow_tools(
    workflow_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    tools = await SQLToolRepository(session).list_by_workflow(workflow_id, tenant.uuid)
    return ApiJSONResponse(content=[_present(t) for t in tools], status_code=status.HTTP_200_OK)


async def delete_workflow_tool(
    workflow_id: UUID,
    tool_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await SQLToolRepository(session).delete(tool_id, workflow_id, tenant.uuid)
    return ApiJSONResponse(content={"deleted": True}, status_code=status.HTTP_200_OK)
