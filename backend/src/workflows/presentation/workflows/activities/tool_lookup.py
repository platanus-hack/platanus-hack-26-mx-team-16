"""Activity: resolve a Tool, render its args with case data and call it (F5 + E3).

Loads the ``ToolDefinition`` + its LOOKUP ``ConnectionAccount`` (the secret +
host allowlist live there), renders ``@slug.path`` / ``{{token}}`` args and the
URL ``{placeholder}`` template against the case's EXTRACTED documents (the
rendering happens HERE, on the non-deterministic side — never in the workflow
sandbox), validates the rendered args vs ``input_schema`` and the response vs
``output_schema``, runs the :class:`DeterministicToolConnector` (HMAC-signed
when the account/tool uses ``auth: "hmac"``; the ``Doxiq-Id`` is the snapshot
uuid), persists the per-case audit snapshot (B1) and finally materialises the
validated payload as a virtual ``WorkflowDocument`` (source=TOOL) via
:class:`CreateVirtualDocument`, so rules see it as ``@slug`` for free.

Error semantics (E3 · plan §4.7):
- config errors (args fail ``input_schema``, unknown token, broken template)
  ⇒ non-retryable ``ApplicationError`` type ``pipeline.enrich_config_error``;
- data conditions (unresolved ref, invalid response, missing doc type) ⇒
  ``DEGRADED`` output, so the phase applies its ``on_failure`` mode.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import jsonschema
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.common.application.logging import get_logger
from src.common.database.models.tool_call_snapshot import ToolCallSnapshotORM
from src.common.domain.entities.workflows.tool_lookup import (
    ENRICH_CONFIG_ERROR_TYPE,
    ToolLookupInput,
    ToolLookupOutput,
)
from src.common.domain.enums.tools import ToolCallStatus
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.common.infrastructure.domain_builder import build_async_domain
from src.connections.infrastructure.repositories.sql_connection_account import (
    SQLConnectionAccountRepository,
)
from src.workflows.application.workflow_documents.virtual_creator import (
    CreateVirtualDocument,
)
from src.workflows.domain.models.tool import ToolDefinition, ToolResult
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.domain.services import token_registry
from src.workflows.domain.services.token_resolver import (
    TokenContext,
    TokenScopeError,
    resolve_all,
)
from src.workflows.infrastructure.repositories.sql_tool import SQLToolRepository
from src.workflows.infrastructure.services.tools.arg_renderer import (
    ToolConfigRenderError,
    UnresolvedRefError,
    collect_doc_refs,
    collect_tokens,
    render_args,
    render_path,
)
from src.workflows.infrastructure.services.tools.connector import (
    DeterministicToolConnector,
)
from src.workflows.presentation.workflows.activities.analysis_run_activities import (
    _flatten_extraction,
)

logger = get_logger(__name__)


class ToolLookupActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        connector: DeterministicToolConnector | None = None,
    ) -> None:
        self._session_maker = session_maker
        if connector is None:
            # F5: inyecta el runner de script según settings (None ⇒ fail-closed).
            from src.workflows.infrastructure.services.tools.script_runner import build_script_runner

            connector = DeterministicToolConnector(script_runner=build_script_runner())
        self._connector = connector

    @activity.defn(name="tool_lookup")
    async def tool_lookup(self, payload: ToolLookupInput) -> ToolLookupOutput:
        data = ToolLookupInput.model_validate(payload)
        # Workflow-scoped (2026-06): la tool solo resuelve dentro de su workflow.
        if data.workflow_id is None:
            logger.warning("tool_lookup.missing_workflow", tool_name=data.tool_name)
            return ToolLookupOutput(status=ToolCallStatus.DEGRADED, error="tool_not_found")
        async with self._session_maker() as session:
            tool = await SQLToolRepository(session).find_by_name(data.tool_name, data.workflow_id, data.tenant_id)
            if tool is None or not tool.enabled:
                logger.warning("tool_lookup.not_found", tool_name=data.tool_name)
                return ToolLookupOutput(status=ToolCallStatus.DEGRADED, error="tool_not_found")

            account = await SQLConnectionAccountRepository(session).find_by_id(
                tool.connection_account_id, data.tenant_id
            )
            secret = account.secret if account else None
            host_allowlist = (account.config or {}).get("host_allowlist") if account else None

            domain = build_async_domain(session)

            # ── render args + URL template (E3: misma sintaxis de reglas) ────
            try:
                args, rendered_path = await self._render(domain, data, tool)
            except ToolConfigRenderError as exc:
                msg = f"tool '{tool.name}': {exc}"
                raise ApplicationError(msg, type=ENRICH_CONFIG_ERROR_TYPE, non_retryable=True) from exc
            except UnresolvedRefError as exc:
                return ToolLookupOutput(status=ToolCallStatus.DEGRADED, error=f"unresolved_ref: {exc}")

            # ── rendered args vs input_schema ⇒ config error (never on_failure)
            if tool.input_schema:
                try:
                    jsonschema.validate(args, tool.input_schema)
                except jsonschema.ValidationError as exc:
                    msg = f"tool '{tool.name}': rendered args do not match input_schema: {exc.message}"
                    raise ApplicationError(msg, type=ENRICH_CONFIG_ERROR_TYPE, non_retryable=True) from exc

            call_tool = tool
            if rendered_path is not None:
                call_tool = tool.model_copy(update={"config": {**(tool.config or {}), "path": rendered_path}})

            # Snapshot uuid doubles as the HMAC `Doxiq-Id` (stable per call).
            snapshot_id = uuid4()
            result = await self._connector.call(
                tool=call_tool,
                secret=secret,
                host_allowlist=host_allowlist,
                args=args,
                call_id=str(snapshot_id),
            )

            # ── response vs output_schema ⇒ on_failure path ──────────────────
            if not result.degraded and tool.output_schema:
                try:
                    jsonschema.validate(result.data, tool.output_schema)
                except jsonschema.ValidationError as exc:
                    result = ToolResult(
                        status=ToolCallStatus.DEGRADED,
                        data=result.data,
                        error=f"output_schema_invalid: {exc.message}"[:500],
                        snapshot=result.snapshot,
                    )

            # B1: per-case audit snapshot (never read back as a cache).
            session.add(
                ToolCallSnapshotORM(
                    uuid=snapshot_id,
                    tenant_id=data.tenant_id,
                    tool_id=tool.uuid,
                    case_id=data.case_id,
                    status=result.status.value,
                    request=result.snapshot,
                    response=result.data,
                    error=result.error,
                )
            )

            # ── persist as virtual document (source=TOOL) ────────────────────
            document_id = None
            should_persist = (not result.degraded) or (data.persist_degraded and result.data is not None)
            if should_persist:
                result, document_id = await self._persist_virtual_document(domain, data, tool, result)

            await session.commit()

        return ToolLookupOutput(status=result.status, data=result.data, error=result.error, document_id=document_id)

    # ── helpers (activity side: free to do I/O) ──────────────────────────────

    async def _render(self, domain, data: ToolLookupInput, tool: ToolDefinition) -> tuple[dict, str | None]:
        raw_args = data.args or {}
        template = (tool.config or {}).get("path") or ""

        refs = collect_doc_refs(raw_args)
        documents: list[EvalDocumentInput] = []
        if refs:
            if data.case_id is None or data.workflow_id is None:
                msg = "args reference case data (@slug) but the run has no case"
                raise UnresolvedRefError(msg)
            documents = await self._load_case_documents(domain, data)

        token_names = collect_tokens(raw_args)
        tokens: dict = {}
        if token_names:
            unknown = sorted(t for t in token_names if not token_registry.is_known(t))
            if unknown:
                msg = f"unknown tokens in args: {', '.join(unknown)}"
                raise ToolConfigRenderError(msg)
            tokens = await self._resolve_tokens(domain, data, token_names)

        args = render_args(raw_args, documents=documents, tokens=tokens)
        rendered_path, consumed = render_path(template, args)
        for key in consumed:
            args.pop(key, None)
        return args, (rendered_path if rendered_path != template else None)

    @staticmethod
    async def _load_case_documents(domain, data: ToolLookupInput) -> list[EvalDocumentInput]:
        """Same shape the rules evaluator feeds to `path_resolver` (E3 reuse)."""
        documents = await domain.document_repository.list_by_case(data.case_id, data.tenant_id)
        extracted = [d for d in documents if d.status.value == "EXTRACTED"]
        doc_types = await domain.document_type_repository.list_by_workflow(data.workflow_id, data.tenant_id)
        slug_by_dt = {dt.uuid: dt.slug for dt in doc_types}
        return [
            EvalDocumentInput(
                document_id=d.uuid,
                document_type_id=d.document_type_id,
                document_type_slug=(slug_by_dt.get(d.document_type_id) if d.document_type_id else None),
                extracted_fields=_flatten_extraction(d.mapped_extraction or d.extraction or {}),
                text=d.extracted_text,
            )
            for d in extracted
        ]

    @staticmethod
    async def _resolve_tokens(domain, data: ToolLookupInput, names: list[str]) -> dict:
        case_name = None
        tenant = None
        if "case.name" in names and data.case_id is not None:
            case = await domain.workflow_case_repository.find_by_id(data.case_id, data.tenant_id)
            case_name = case.name if case else None
        if "tenant.name" in names:
            tenant = await domain.tenant_repository.find(data.tenant_id)
        context = TokenContext(case_name=case_name, tenant=tenant, run_id=None, rule=None, now=datetime.now(UTC))
        try:
            return resolve_all(names, context)
        except TokenScopeError as exc:
            raise UnresolvedRefError(str(exc)) from exc

    @staticmethod
    async def _persist_virtual_document(
        domain, data: ToolLookupInput, tool: ToolDefinition, result: ToolResult
    ) -> tuple[ToolResult, object | None]:
        slug = data.output_doc_type_slug or tool.name
        if data.case_id is None or data.workflow_id is None:
            degraded = ToolResult(
                status=ToolCallStatus.DEGRADED,
                data=result.data,
                error="case_required: cannot persist the tool result as a virtual document without a case",
                snapshot=result.snapshot,
            )
            return degraded, None
        try:
            document = await CreateVirtualDocument(
                tenant_id=data.tenant_id,
                workflow_id=data.workflow_id,
                case_id=data.case_id,
                doc_type_slug=slug,
                payload=result.data or {},
                source=WorkflowDocumentSource.TOOL,
                document_repository=domain.document_repository,
                document_type_repository=domain.document_type_repository,
            ).execute()
        except DocumentTypeNotFoundError:
            logger.warning("tool_lookup.doc_type_not_found", tool_name=tool.name, slug=slug)
            degraded = ToolResult(
                status=ToolCallStatus.DEGRADED,
                data=result.data,
                error=(
                    f"doc_type_not_found: document type '{slug}' must exist in the workflow "
                    "(create it or set output_doc_type_slug)"
                ),
                snapshot=result.snapshot,
            )
            return degraded, None
        return result, document.uuid
