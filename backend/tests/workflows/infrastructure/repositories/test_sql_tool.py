"""SQLToolRepository — round-trip de script tools sin cuenta de conexión (F5).

Las script tools (PYTHON/JS) corren en sandbox y no referencian una
ConnectionAccount; ``connection_account_id`` debe persistir y releerse como NULL.
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_none, contain, equal, expect

from src.common.domain.enums.tools import ToolTransport
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.infrastructure.repositories.sql_tool import SQLToolRepository


async def test_upsert__script_tool_persists_without_connection_account(async_session, tenant_orm, workflow_orm):
    repo = SQLToolRepository(async_session)
    tool = ToolDefinition(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="normalize_drug",
        display_name="Normalize drug",
        transport=ToolTransport.PYTHON,
        connection_account_id=None,
        config={
            "runtime": "python3.12",
            "entrypoint": "main",
            "code": "def main(args):\n    return args",
        },
    )

    saved = await repo.upsert(tool)

    expect(saved.connection_account_id).to(be_none)
    expect(saved.transport).to(equal(ToolTransport.PYTHON))

    reloaded = await repo.find_by_name("normalize_drug", workflow_orm.uuid, tenant_orm.uuid)

    expect(reloaded).to_not(be_none)
    expect(reloaded.connection_account_id).to(be_none)
    expect(reloaded.transport).to(equal(ToolTransport.PYTHON))
    expect(reloaded.config["code"]).to(contain("def main"))
