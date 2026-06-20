"""workflow_tools._present — serialización de connection_account_id (F5).

Script tools (PYTHON/JS) no llevan cuenta de conexión ⇒ el presenter debe emitir
``null`` sin reventar; las HTTP serializan el uuid como string.
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.enums.tools import ToolTransport
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.presentation.endpoints.workflow_tools import _present


def test_present__script_tool_has_null_connection_account():
    tool = ToolDefinition(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="t",
        display_name="T",
        transport=ToolTransport.PYTHON,
        connection_account_id=None,
        config={"code": "def main(args):\n    return args"},
    )

    out = _present(tool)

    expect(out["connection_account_id"]).to(be_none)
    expect(out["transport"]).to(equal("PYTHON"))


def test_present__http_tool_serializes_connection_account():
    account_id = uuid4()
    tool = ToolDefinition(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="t",
        display_name="T",
        transport=ToolTransport.HTTP,
        connection_account_id=account_id,
    )

    out = _present(tool)

    expect(out["connection_account_id"]).to(equal(str(account_id)))
    expect(out["transport"]).to(equal("HTTP"))
