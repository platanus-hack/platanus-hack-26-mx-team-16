"""E3: tool_lookup activity — render, schema validation, virtual-doc persistence.

Unit-style (no DB): repos/use case are monkeypatched on the activity module and
the connector is injected, so the tests pin the orchestration contract:
config error (ApplicationError) vs on_failure (DEGRADED output), snapshot uuid
== HMAC call id, and CreateVirtualDocument receiving the validated payload.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import contain, equal, expect
from temporalio.exceptions import ApplicationError

from src.common.domain.entities.workflows.tool_lookup import (
    ENRICH_CONFIG_ERROR_TYPE,
    ToolLookupInput,
)
from src.common.domain.enums.tools import ToolCallStatus
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.workflows.domain.models.tool import ToolDefinition, ToolResult
from src.workflows.presentation.workflows.activities import tool_lookup as tl

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_DOC_ID = UUID("55555555-5555-5555-5555-555555555555")
_DT_ID = UUID("66666666-6666-6666-6666-666666666666")


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


def _maker(session):
    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return False

    return lambda: _Ctx()


class _FakeConnector:
    def __init__(self, result: ToolResult):
        self.result = result
        self.calls = []

    async def call(self, *, tool, secret, host_allowlist, args, call_id=None, now=None):
        self.calls.append({"tool": tool, "args": args, "call_id": call_id})
        return self.result


def _tool(**overrides) -> ToolDefinition:
    fields: dict = {
        "uuid": uuid4(),
        "tenant_id": _TENANT,
        "workflow_id": _WORKFLOW,
        "name": "lookup_poliza",
        "display_name": "Lookup Póliza",
        "connection_account_id": uuid4(),
        "config": {"base_url": "https://api.example.com", "path": "/lookup"},
    }
    fields.update(overrides)
    return ToolDefinition(**fields)


def _async(value):
    async def _f(*args, **kwargs):
        return value

    return _f


def _domain():
    docs = [
        SimpleNamespace(
            uuid=uuid4(),
            status=SimpleNamespace(value="EXTRACTED"),
            document_type_id=_DT_ID,
            mapped_extraction={"numero": "123"},
            extraction=None,
            extracted_text=None,
        )
    ]
    doc_types = [SimpleNamespace(uuid=_DT_ID, slug="oficio")]
    return SimpleNamespace(
        document_repository=SimpleNamespace(list_by_case=_async(docs)),
        document_type_repository=SimpleNamespace(list_by_workflow=_async(doc_types)),
        workflow_case_repository=SimpleNamespace(find_by_id=_async(None)),
        tenant_repository=SimpleNamespace(find=_async(None)),
    )


def _patch(monkeypatch, *, tool, created_doc_id=_DOC_ID, create_raises=None):
    monkeypatch.setattr(tl, "SQLToolRepository", lambda s: SimpleNamespace(find_by_name=_async(tool)))
    account = SimpleNamespace(secret="whsec_x", config={"host_allowlist": ["api.example.com"]})
    monkeypatch.setattr(tl, "SQLConnectionAccountRepository", lambda s: SimpleNamespace(find_by_id=_async(account)))
    monkeypatch.setattr(tl, "build_async_domain", lambda s: _domain())

    created: list[dict] = []

    class _FakeCreateVirtual:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created.append(kwargs)

        async def execute(self):
            if create_raises is not None:
                raise create_raises
            return SimpleNamespace(uuid=created_doc_id)

    monkeypatch.setattr(tl, "CreateVirtualDocument", _FakeCreateVirtual)
    return created


def _input(**overrides) -> ToolLookupInput:
    fields: dict = {
        "tenant_id": _TENANT,
        "tool_name": "lookup_poliza",
        "case_id": _CASE,
        "workflow_id": _WORKFLOW,
    }
    fields.update(overrides)
    return ToolLookupInput(**fields)


def _activity(connector: _FakeConnector, session: _FakeSession | None = None) -> tl.ToolLookupActivity:
    return tl.ToolLookupActivity(session_maker=_maker(session or _FakeSession()), connector=connector)


# ── persistence as virtual document ─────────────────────────────────────────


async def test_tool_lookup__ok_persists_virtual_tool_document(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={"saldo": 10}, snapshot={"url": "u"}))
    created = _patch(monkeypatch, tool=_tool())
    session = _FakeSession()

    output = await _activity(connector, session).tool_lookup(_input(output_doc_type_slug="poliza"))

    expect(output.status).to(equal(ToolCallStatus.OK))
    expect(output.document_id).to(equal(_DOC_ID))
    expect(len(created)).to(equal(1))
    expect(created[0]["doc_type_slug"]).to(equal("poliza"))
    expect(created[0]["source"]).to(equal(WorkflowDocumentSource.TOOL))
    expect(created[0]["payload"]).to(equal({"saldo": 10}))
    expect(created[0]["case_id"]).to(equal(_CASE))
    # Snapshot uuid doubles as the HMAC Doxiq-Id passed to the connector.
    expect(str(session.added[0].uuid)).to(equal(connector.calls[0]["call_id"]))
    expect(session.committed).to(equal(True))


async def test_tool_lookup__doc_type_slug_falls_back_to_tool_name(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    created = _patch(monkeypatch, tool=_tool())

    await _activity(connector).tool_lookup(_input())

    expect(created[0]["doc_type_slug"]).to(equal("lookup_poliza"))


async def test_tool_lookup__missing_doc_type_degrades_with_clear_error(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={"x": 1}))
    _patch(monkeypatch, tool=_tool(), create_raises=DocumentTypeNotFoundError("poliza"))

    output = await _activity(connector).tool_lookup(_input(output_doc_type_slug="poliza"))

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(contain("doc_type_not_found"))
    expect(output.error).to(contain("poliza"))
    expect(output.document_id).to(equal(None))


async def test_tool_lookup__degraded_not_persisted_unless_persist_degraded(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.DEGRADED, data={"part": 1}, error="http_500"))
    created = _patch(monkeypatch, tool=_tool())

    output = await _activity(connector).tool_lookup(_input())
    expect(len(created)).to(equal(0))
    expect(output.document_id).to(equal(None))

    output = await _activity(connector).tool_lookup(_input(persist_degraded=True))
    expect(len(created)).to(equal(1))
    expect(output.document_id).to(equal(_DOC_ID))


async def test_tool_lookup__without_case_cannot_persist_and_degrades(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    created = _patch(monkeypatch, tool=_tool())

    output = await _activity(connector).tool_lookup(_input(case_id=None))

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(contain("case_required"))
    expect(len(created)).to(equal(0))


async def test_tool_lookup__without_workflow_degrades_as_not_found(monkeypatch):
    # Workflow-scoped (2026-06): sin workflow_id no hay scope donde resolver.
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    created = _patch(monkeypatch, tool=_tool())

    output = await _activity(connector).tool_lookup(_input(case_id=None, workflow_id=None))

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(equal("tool_not_found"))
    expect(len(created)).to(equal(0))


# ── render: @slug args, {{token}} and {placeholder} path ────────────────────


async def test_tool_lookup__renders_args_and_path_from_case_documents(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    _patch(monkeypatch, tool=_tool(config={"base_url": "https://api.example.com", "path": "/lookup/{q}"}))

    await _activity(connector).tool_lookup(_input(args={"q": "@oficio.numero", "at": "{{today}}"}))

    call = connector.calls[0]
    # {q} consumed by the path; {{today}} rendered to today's ISO date.
    expect(call["tool"].config["path"]).to(equal("/lookup/123"))
    expect(call["args"]).to(equal({"at": datetime.now(UTC).date().isoformat()}))


async def test_tool_lookup__unresolved_ref_degrades_for_on_failure(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    _patch(monkeypatch, tool=_tool())

    output = await _activity(connector).tool_lookup(_input(args={"q": "@poliza.numero"}))

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(contain("unresolved_ref"))
    expect(len(connector.calls)).to(equal(0))  # never calls the upstream


async def test_tool_lookup__refs_without_case_degrade(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    _patch(monkeypatch, tool=_tool())

    output = await _activity(connector).tool_lookup(_input(case_id=None, args={"q": "@oficio.numero"}))

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(contain("unresolved_ref"))


# ── schema validation: config error vs on_failure ───────────────────────────


async def test_tool_lookup__args_failing_input_schema_is_config_error(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    schema = {"type": "object", "required": ["q"], "properties": {"q": {"type": "string"}}}
    _patch(monkeypatch, tool=_tool(input_schema=schema))

    try:
        await _activity(connector).tool_lookup(_input(args={}))
        raise AssertionError("expected ApplicationError")
    except ApplicationError as exc:
        expect(exc.type).to(equal(ENRICH_CONFIG_ERROR_TYPE))
        expect(exc.non_retryable).to(equal(True))

    expect(len(connector.calls)).to(equal(0))


async def test_tool_lookup__unknown_token_is_config_error(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    _patch(monkeypatch, tool=_tool())

    try:
        await _activity(connector).tool_lookup(_input(args={"x": "{{no_such_token}}"}))
        raise AssertionError("expected ApplicationError")
    except ApplicationError as exc:
        expect(exc.type).to(equal(ENRICH_CONFIG_ERROR_TYPE))


async def test_tool_lookup__response_failing_output_schema_goes_on_failure(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={"saldo": "diez"}))
    schema = {"type": "object", "properties": {"saldo": {"type": "number"}}, "required": ["saldo"]}
    created = _patch(monkeypatch, tool=_tool(output_schema=schema))

    output = await _activity(connector).tool_lookup(_input())

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(contain("output_schema_invalid"))
    expect(len(created)).to(equal(0))  # invalid payload is not persisted


# ── existing degraded paths stay intact ─────────────────────────────────────


async def test_tool_lookup__tool_not_found_degrades(monkeypatch):
    connector = _FakeConnector(ToolResult(status=ToolCallStatus.OK, data={}))
    _patch(monkeypatch, tool=None)

    output = await _activity(connector).tool_lookup(_input())

    expect(output.status).to(equal(ToolCallStatus.DEGRADED))
    expect(output.error).to(equal("tool_not_found"))
