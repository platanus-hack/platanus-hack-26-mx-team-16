"""Temporal activities for the WorkflowAnalysisRunWorkflow.

Each activity owns its own DB session (or just the Redis publisher) so
the deterministic workflow body never touches I/O directly. Activities
return Pydantic payloads carried back to the workflow by the
`pydantic_data_converter`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from datetime import UTC, datetime
from typing import Any

from src.common.application.helpers.json_encoder import convert_to_camel_case
from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    AnalysisRunPlan,
    AnalysisRunWorkflowInput,
    CombinationPayload,
    CompleteAnalysisRunInput,
    EvaluateCombinationInput,
    EvaluateCombinationOutput,
    UpdateAnalysisRunStatusInput,
)
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.infrastructure.domain_builder import build_async_domain
from src.common.infrastructure.event_publisher import RedisEventPublisher
from src.knowledge_base.domain.services.knowledge_context import build_knowledge_context
from src.workflows.domain.services.token_resolver import TokenContext, resolve_all
from src.workflows.application.analysis_run_summary.complete_run import (
    CompleteWorkflowAnalysisRun,
)
from src.workflows.application.analysis_run_summary.webhook_dispatcher import (
    SummaryWebhookDispatcher,
)
from src.workflows.application.workflow_rules.evaluation.evaluator import (
    WorkflowRuleEvaluator,
)
from src.workflows.application.workflow_rules.evaluation.scope_resolver import (
    Combination,
    ScopedDocument,
    resolve_scope,
)
from src.workflows.domain.events.workflow_analysis_run_event import (
    WorkflowAnalysisRunEvent,
)
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
)
from src.workflows.presentation.presenters.workflow_rule_result import (
    WorkflowRuleResultPresenter,
)

logger = get_logger(__name__)

# Status string used by the evaluator's "synthetic_empty" branch + the
# verdict aggregator. Kept as a string so we don't drag the SQLAlchemy
# import chain into the workflow sandbox via this module.
_PASSED_STATUSES = {WorkflowRuleResultStatus.SUCCESS}


def select_rules_in_set(rules: list, rule_set: str | None) -> list:
    """phases-config · analyze.rule_set: filtra las reglas a un subconjunto
    nombrado. El set es un tag declarado en ``rule.config.rule_sets`` (lista de
    strings); sin entidad nueva. ``None``/vacío ⇒ todas las reglas (comportamiento
    de hoy). Extraído a función de módulo para poder testearlo sin harness de BD.
    """
    if not rule_set:
        return rules
    selected = []
    for r in rules:
        tags = (getattr(r, "config", None) or {}).get("rule_sets")
        # `rule_sets` debería ser list[str], pero ningún schema lo fuerza hoy: un
        # escalar ("billing") degradaría a match por substring. Coaccionamos.
        if not isinstance(tags, list | tuple | set):
            tags = []
        if rule_set in tags:
            selected.append(r)
    return selected


class LoadAnalysisRunPlanActivity:
    """Loads everything needed to evaluate the run and emits an execution plan."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="load_analysis_run_plan")
    async def load_analysis_run_plan(self, payload: AnalysisRunWorkflowInput) -> AnalysisRunPlan:
        data = AnalysisRunWorkflowInput.model_validate(payload)

        async with self._session_maker() as session:
            domain = build_async_domain(session)

            case = await domain.workflow_case_repository.find_by_id(data.case_id, data.tenant_id)
            case_name = case.name if case else None

            rules = await domain.workflow_rule_repository.list_by_workflow(data.workflow_id, data.tenant_id)
            active_rules = [r for r in rules if r.is_active and r.current_compilation_id is not None]
            # phases-config · analyze.rule_set: subconjunto nombrado (tag en
            # ``rule.config.rule_sets``; sin entidad nueva). None ⇒ todas (hoy).
            selected_rules = select_rules_in_set(active_rules, data.rule_set)
            if data.rule_set and active_rules and not selected_rules:
                # Un rule_set con typo deja el caso sin reglas en SILENCIO: el run
                # cierra COMPLETED con verdict vacío. Lo dejamos auditable.
                logger.warning(
                    "analysis_run.rule_set_matched_nothing",
                    rule_set=data.rule_set,
                    workflow_id=str(data.workflow_id),
                    active_rules=len(active_rules),
                )
            active_rules = selected_rules

            documents = await domain.document_repository.list_by_case(data.case_id, data.tenant_id)
            extracted_docs = [d for d in documents if d.status.value == "EXTRACTED"]

            doc_types = await domain.document_type_repository.list_by_workflow(data.workflow_id, data.tenant_id)
            slug_by_dt = {dt.uuid: dt.slug for dt in doc_types}

            evaluations: list[CombinationPayload] = []
            for rule in active_rules:
                combos = resolve_scope(
                    scope=rule.scope or {},
                    documents=extracted_docs,
                    slug_by_document_type=slug_by_dt,
                )
                for idx, combo in enumerate(combos):
                    evaluations.append(
                        CombinationPayload(
                            rule_id=rule.uuid,
                            combination_index=idx,
                            document_refs=combo.document_refs,
                            document_refs_hash=combo.document_refs_hash,
                            document_ids=[d.document_id for d in combo.documents],
                            is_synthetic_empty=combo.is_synthetic_empty,
                            synthetic_outcome=(combo.synthetic_outcome.value if combo.synthetic_outcome else None),
                        )
                    )

        return AnalysisRunPlan(
            run_id=data.run_id,
            workflow_id=data.workflow_id,
            case_id=data.case_id,
            tenant_id=data.tenant_id,
            case_name=case_name,
            evaluations=evaluations,
            providers=data.providers,
        )


class EvaluateRuleCombinationActivity:
    """Evaluates one (rule, combination) and persists the WorkflowRuleResult."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="evaluate_rule_combination")
    async def evaluate_rule_combination(self, payload: EvaluateCombinationInput) -> EvaluateCombinationOutput:
        data = EvaluateCombinationInput.model_validate(payload)
        combo = data.combination

        async with self._session_maker() as session:
            domain = build_async_domain(session)

            rule = await domain.workflow_rule_repository.find_by_id(combo.rule_id, data.tenant_id)
            if rule is None:
                raise RuntimeError(f"rule not found: {combo.rule_id}")

            doc_types = await domain.document_type_repository.list_by_workflow(data.workflow_id, data.tenant_id)
            slug_by_dt = {dt.uuid: dt.slug for dt in doc_types}

            document_inputs: list[EvalDocumentInput] = []
            if combo.document_ids:
                all_docs = await domain.document_repository.list_by_case(data.case_id, data.tenant_id)
                docs_index = {d.uuid: d for d in all_docs}
                for did in combo.document_ids:
                    doc = docs_index.get(did)
                    if doc is None:
                        continue
                    fields = doc.mapped_extraction or doc.extraction or {}
                    document_inputs.append(
                        EvalDocumentInput(
                            document_id=doc.uuid,
                            document_type_id=doc.document_type_id,
                            document_type_slug=(
                                slug_by_dt.get(doc.document_type_id) if doc.document_type_id else None
                            ),
                            # Extracted fields land here as `{value, bbox}`
                            # objects per the extraction pipeline. Flatten
                            # them to the scalar `value` so rule prompts
                            # like `@cedula.numero` see "13021132" instead
                            # of the wrapper dict (which would break
                            # FORMAT/RANGE/AGGREGATE checks).
                            extracted_fields=_flatten_extraction(fields),
                            text=doc.extracted_text,
                        )
                    )

            # Resolve `{{tokens}}` declared by the compilation so checks
            # like DATE_CHECK against `{{today}}` don't error with
            # "token not declared in `tokens`".
            tenant = await domain.tenant_repository.find(data.tenant_id)
            tokens = await _resolve_rule_tokens(
                rule=rule,
                compilation_repository=domain.workflow_rule_compilation_repository,
                tenant=tenant,
                case_name=data.case_name,
                run_id=data.run_id,
            )

            combination = Combination(
                documents=[
                    ScopedDocument(
                        document_id=d.document_id,
                        document_type_id=d.document_type_id,
                        document_type_slug=d.document_type_slug,
                    )
                    for d in document_inputs
                ],
                document_refs=combo.document_refs,
                is_synthetic_empty=combo.is_synthetic_empty,
            )

            # F5/B2 fix: hydrate the rule's KB refs instead of passing `[]`, so
            # `#kb` references (e.g. drug normalisation) actually resolve.
            knowledge_context = await build_knowledge_context(
                domain.kb_document_repository, data.tenant_id, rule.knowledge_refs
            )

            # phases-config · analyze.{parser,reviewer}_provider: kind con runners
            # override para ESTE run; None si no hay overrides ⇒ registry global
            # (byte-idéntico). build_kind devuelve None para kinds sin LLM.
            kind_override = None
            if data.providers.parser or data.providers.reviewer:
                from src.workflows.infrastructure.services.rules.bootstrap import build_kind  # noqa: PLC0415

                kind_override = build_kind(
                    rule.kind,
                    parser_provider=data.providers.parser,
                    evaluator_provider=data.providers.reviewer,
                )

            try:
                result = await WorkflowRuleEvaluator(
                    rule=rule,
                    combination=combination,
                    workflow_analysis_run_id=data.run_id,
                    case_id=data.case_id,
                    document_inputs=document_inputs,
                    knowledge_context=knowledge_context,
                    tokens=tokens,
                    compilation_repository=domain.workflow_rule_compilation_repository,
                    result_repository=domain.workflow_rule_result_repository,
                    kind_override=kind_override,
                ).execute()
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        # Reuse the presenter that the REST API uses so the payload
        # shape sent over SSE is identical to what the frontend already
        # parses for `AnalysisRuleResult`. Pass through `convert_to_camel_case`
        # to unwrap `RawJson` markers and convert keys — Pydantic/Temporal
        # cannot serialize `RawJson` directly via `to_json`.
        result_payload = convert_to_camel_case(
            WorkflowRuleResultPresenter(instance=result, rule_name=rule.name).to_dict
        )
        is_passed = _derive_is_passed(result)

        return EvaluateCombinationOutput(
            rule_id=combo.rule_id,
            result_uuid=result.uuid,
            status=result.status.value,
            is_passed=is_passed,
            has_error=bool(result.error),
            error=result.error,
            result_payload=result_payload,
        )


def _flatten_extraction(fields: dict[str, Any]) -> dict[str, Any]:
    """Unwrap `{value, bbox}` extraction shapes to scalar `value`.

    The extraction pipeline persists each field as
    `{"value": "...", "bbox": [...]}`. Rule prompts reference fields by
    name (`@cedula.numero`) and expect the scalar, not the wrapper. We
    walk one level deep and replace any dict that has a `value` key with
    that value. Untouched fields (nested objects without `value`,
    primitives, lists) pass through verbatim so rules that genuinely
    need to traverse structure can still do so.
    """
    if not isinstance(fields, dict):
        return fields
    out: dict[str, Any] = {}
    for k, v in fields.items():
        if isinstance(v, dict) and "value" in v and "bbox" in v:
            out[k] = v["value"]
        else:
            out[k] = v
    return out


async def _resolve_rule_tokens(
    *,
    rule,
    compilation_repository,
    tenant,
    case_name: str | None,
    run_id,
) -> dict[str, Any]:
    """Resolve `{{tokens}}` declared in the rule's compilation artifact."""
    if rule.current_compilation_id is None:
        return {}
    compilation = await compilation_repository.find_by_id(rule.current_compilation_id)
    if compilation is None or not compilation.artifact:
        return {}

    declared: set[str] = set()
    for sub_check in compilation.artifact.get("sub_checks") or []:
        for t in sub_check.get("tokens") or []:
            declared.add(t)
    if not declared:
        return {}

    ctx = TokenContext(
        case_name=case_name,
        tenant=tenant,
        run_id=run_id,
        rule=rule,
        now=datetime.now(UTC),
    )
    try:
        return resolve_all(declared, ctx)
    except Exception:
        logger.warning(
            "analysis_run.token_resolution_failed",
            rule_id=str(rule.uuid),
            tokens=list(declared),
        )
        return {}


def _derive_is_passed(result) -> bool | None:
    """Best-effort verdict signal for progress counters.

    Authoritative pass/fail counts come from the VerdictAggregator in
    `CompleteWorkflowAnalysisRun`; this is just for the live progress
    counters on the SSE stream.
    """
    if result.status not in _PASSED_STATUSES:
        return None
    output = result.output or {}
    raw = output.get("passed")
    if isinstance(raw, bool):
        return raw
    return None


class UpdateAnalysisRunStatusActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="update_analysis_run_status")
    async def update_analysis_run_status(self, payload: UpdateAnalysisRunStatusInput) -> None:
        data = UpdateAnalysisRunStatusInput.model_validate(payload)
        async with self._session_maker() as session:
            domain = build_async_domain(session)
            await domain.workflow_analysis_run_repository.update_status(
                run_id=data.run_id,
                tenant_id=data.tenant_id,
                status=data.status,
                error=data.error,
                completed=data.completed,
                canceled_by=data.canceled_by,
                rules_passed=data.rules_passed,
                rules_failed=data.rules_failed,
                rules_inconclusive=data.rules_inconclusive,
            )
            await session.commit()


class PublishAnalysisRunEventActivity:
    """Thin wrapper around RedisEventPublisher for a `WorkflowAnalysisRunEvent`."""

    def __init__(self, event_publisher: RedisEventPublisher) -> None:
        self._event_publisher = event_publisher

    @activity.defn(name="publish_analysis_run_event")
    async def publish_analysis_run_event(self, event: WorkflowAnalysisRunEvent) -> None:
        await self._event_publisher.publish(event)


class CompleteAnalysisRunActivity:
    """Closes the run (status COMPLETED) and triggers the verdict + narrative summary."""

    def __init__(
        self,
        session_maker: async_sessionmaker,
        synthesizer_agent: SynthesizerAgent,
        event_publisher: RedisEventPublisher,
        webhook_dispatcher: SummaryWebhookDispatcher | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._agent = synthesizer_agent
        self._event_publisher = event_publisher
        self._webhook_dispatcher = webhook_dispatcher

    @activity.defn(name="complete_analysis_run")
    async def complete_analysis_run(self, payload: CompleteAnalysisRunInput) -> None:
        data = CompleteAnalysisRunInput.model_validate(payload)
        # phases-config · analyze.synthesizer_provider: synthesizer per-call con
        # override; sin override usa el singleton del worker (env, hoy).
        agent = self._agent
        if data.providers.synthesizer:
            from src.workflows.infrastructure.services.rules.bootstrap import build_synthesizer_agent  # noqa: PLC0415

            agent = build_synthesizer_agent(data.providers.synthesizer)
        async with self._session_maker() as session:
            domain = build_async_domain(session)
            tenant = await domain.tenant_repository.find(data.tenant_id)
            if tenant is None:
                raise RuntimeError(f"tenant not found: {data.tenant_id}")
            await CompleteWorkflowAnalysisRun(
                tenant=tenant,
                run_id=data.run_id,
                tenant_id=data.tenant_id,
                workflow_repository=domain.workflow_repository,
                run_repository=domain.workflow_analysis_run_repository,
                rule_repository=domain.workflow_rule_repository,
                result_repository=domain.workflow_rule_result_repository,
                summary_repository=domain.run_summary_repository,
                agent=agent,
                event_publisher=self._event_publisher,
                webhook_dispatcher=self._webhook_dispatcher,
                document_repository=domain.document_repository,
            ).execute()
            await session.commit()
