"""F5 · D-D: transportes PYTHON/JS — dispatch al runner sandbox + fail-closed.

El connector NO hace HTTP para script tools: las rutea al ScriptRunner aislado.
Sin runner provisionado degrada (fail-closed); un fallo del runner también degrada
(mismo contrato B1 que HTTP). La ejecución real (gVisor/Firecracker) es ops + ADR 0006.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from expects import be_none, contain, equal, expect

from src.common.domain.enums.tools import ToolCallStatus, ToolTransport
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.infrastructure.services.tools.connector import DeterministicToolConnector
from src.workflows.infrastructure.services.tools.script_runner import (
    LocalSubprocessScriptRunner,
    ScriptExecutionError,
    ScriptSandboxNotConfiguredError,
    UnconfiguredScriptRunner,
    build_script_runner,
)


def _script_tool(transport: ToolTransport = ToolTransport.PYTHON, **config) -> ToolDefinition:
    return ToolDefinition(
        uuid=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        workflow_id=UUID("33333333-3333-3333-3333-333333333333"),
        name="score_risk",
        display_name="Score Risk",
        transport=transport,
        connection_account_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        config={"runtime": "python3.12", "entrypoint": "main", "code": "...", **config},
    )


class _OkRunner:
    async def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"risk": 0.42, "echo_args": kwargs["args"]}


class _BoomRunner:
    async def run(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("isolation breach")


def test_transport_enum__has_python_and_js():
    expect({ToolTransport.PYTHON.value, ToolTransport.JS.value}).to(equal({"PYTHON", "JS"}))


async def test_script_tool__no_runner_degrades_fail_closed():
    connector = DeterministicToolConnector(script_runner=None)

    result = await connector.call(tool=_script_tool(), secret=None, host_allowlist=None, args={"x": 1})

    expect(result.status).to(equal(ToolCallStatus.DEGRADED))
    expect(result.error).to(contain("script_sandbox_not_configured"))
    expect(result.data).to(be_none)


async def test_script_tool__runner_executes_and_returns_data():
    connector = DeterministicToolConnector(script_runner=_OkRunner())

    result = await connector.call(
        tool=_script_tool(transport=ToolTransport.JS), secret=None, host_allowlist=None, args={"x": 1}
    )

    expect(result.status).to(equal(ToolCallStatus.OK))
    expect(result.data).to(equal({"risk": 0.42, "echo_args": {"x": 1}}))


async def test_script_tool__runner_failure_degrades_never_raises():
    connector = DeterministicToolConnector(script_runner=_BoomRunner())

    result = await connector.call(tool=_script_tool(), secret=None, host_allowlist=None, args={})

    expect(result.status).to(equal(ToolCallStatus.DEGRADED))
    expect(result.error).to(contain("script_failed"))


async def test_unconfigured_runner__raises_fail_closed():
    runner = UnconfiguredScriptRunner()

    raised = False
    try:
        await runner.run(
            transport=ToolTransport.PYTHON,
            runtime="python3.12",
            entrypoint="m",
            code="x",
            code_ref=None,
            args={},
            limits={},
        )
    except ScriptSandboxNotConfiguredError:
        raised = True

    expect(raised).to(equal(True))


# ── G6 · local subprocess runner (dev-only) ─────────────────────────────────


def test_build_script_runner__default_is_fail_closed_none():
    # Sin TOOLS_SCRIPT_RUNNER configurado ⇒ None ⇒ el connector degrada.
    expect(build_script_runner()).to(be_none)


async def test_local_runner__executes_python_and_returns_json():
    runner = LocalSubprocessScriptRunner()

    result = await runner.run(
        transport=ToolTransport.PYTHON,
        runtime="python3.12",
        entrypoint="main",
        code="def main(args):\n    return {'sum': args['a'] + args['b']}",
        code_ref=None,
        args={"a": 2, "b": 3},
        limits={},
    )

    expect(result).to(equal({"sum": 5}))


async def test_local_runner__script_error_raises_execution_error():
    runner = LocalSubprocessScriptRunner()

    async def _boom():
        await runner.run(
            transport=ToolTransport.PYTHON,
            runtime="python3.12",
            entrypoint="main",
            code="def main(args):\n    raise ValueError('boom')",
            code_ref=None,
            args={},
            limits={},
        )

    with pytest.raises(ScriptExecutionError):
        await _boom()


async def test_connector_with_local_runner__python_tool_returns_ok():
    connector = DeterministicToolConnector(script_runner=LocalSubprocessScriptRunner())
    tool = _script_tool(
        transport=ToolTransport.PYTHON,
        runtime="python3.12",
        entrypoint="main",
        code="def main(args):\n    return {'echo': args}",
    )

    result = await connector.call(tool=tool, secret=None, host_allowlist=None, args={"q": "hi"})

    expect(result.status).to(equal(ToolCallStatus.OK))
    expect(result.data).to(equal({"echo": {"q": "hi"}}))
