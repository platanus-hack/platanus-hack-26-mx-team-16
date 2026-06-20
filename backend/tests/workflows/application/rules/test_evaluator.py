"""Tests for WorkflowRuleEvaluator (spec §3.3, §7.2)."""

from uuid import uuid4

import pytest
from expects import be_true, contain, equal, expect

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleCompilationStatus,
    WorkflowRuleOnEmpty,
    WorkflowRuleResultStatus,
)
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.workflows.application.workflow_rules.evaluation.evaluator import WorkflowRuleEvaluator
from src.workflows.application.workflow_rules.evaluation.scope_resolver import Combination
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput, EvaluationOutcome


def _validation_rule(tenant_id):
    compilation_id = uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="check",
        config={"severity": "MAJOR"},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        current_compilation_id=compilation_id,
    )
    compilation = WorkflowRuleCompilation(
        uuid=compilation_id,
        rule_id=rule.uuid,
        version=1,
        kind="VALIDATION",
        status=WorkflowRuleCompilationStatus.READY,
        artifact={"prompt": "check", "available_slugs": [], "sub_checks": []},
    )
    return rule, compilation


@pytest.fixture
def synthetic_combo_skipped():
    return Combination(
        documents=[],
        document_refs={},
        is_synthetic_empty=True,
        synthetic_outcome=WorkflowRuleOnEmpty.SKIPPED,
    )


@pytest.fixture
def synthetic_combo_failed():
    return Combination(
        documents=[],
        document_refs={},
        is_synthetic_empty=True,
        synthetic_outcome=WorkflowRuleOnEmpty.FAILED,
    )


async def test_execute__synthetic_skipped_persists_skipped_status(
    tenant_id,
    synthetic_combo_skipped,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, _ = _validation_rule(tenant_id)
    workflow_rule_result_repository.upsert.side_effect = lambda r: r

    evaluator = WorkflowRuleEvaluator(
        rule=rule,
        combination=synthetic_combo_skipped,
        workflow_analysis_run_id=uuid4(),
        case_id=uuid4(),
        document_inputs=[],
        knowledge_context=[],
        tokens={},
        compilation_repository=workflow_rule_compilation_repository,
        result_repository=workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.SKIPPED))
    expect(result.output).to(equal(None))


async def test_execute__synthetic_failed_persists_success_with_passed_false(
    tenant_id,
    synthetic_combo_failed,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    """Spec §7.2 — `on_empty=FAILED` keeps status=SUCCESS; semantics live in output.passed."""
    rule, _ = _validation_rule(tenant_id)
    workflow_rule_result_repository.upsert.side_effect = lambda r: r

    evaluator = WorkflowRuleEvaluator(
        rule=rule,
        combination=synthetic_combo_failed,
        workflow_analysis_run_id=uuid4(),
        case_id=uuid4(),
        document_inputs=[],
        knowledge_context=[],
        tokens={},
        compilation_repository=workflow_rule_compilation_repository,
        result_repository=workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.SUCCESS))
    expect(result.output).to(equal({"passed": False, "reason": "scope vacío"}))


async def test_execute__missing_compilation_persists_errored(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, _ = _validation_rule(tenant_id)
    rule.current_compilation_id = None
    combo = Combination(documents=[], document_refs={"invoice": [str(uuid4())]})
    workflow_rule_result_repository.upsert.side_effect = lambda r: r

    evaluator = WorkflowRuleEvaluator(
        rule=rule,
        combination=combo,
        workflow_analysis_run_id=uuid4(),
        case_id=uuid4(),
        document_inputs=[],
        knowledge_context=[],
        tokens={},
        compilation_repository=workflow_rule_compilation_repository,
        result_repository=workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.ERRORED))


# ---------------- E5 · `when` por regla ---------------- #


def _persona_doc(tipo_entidad: str) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="persona",
        extracted_fields={"tipo_entidad": tipo_entidad, "ci": "1234567"},
    )


def _evaluator_for_when(
    rule,
    compilation,
    documents,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    workflow_rule_compilation_repository.find_by_id.return_value = compilation
    workflow_rule_result_repository.upsert.side_effect = lambda r: r
    return WorkflowRuleEvaluator(
        rule=rule,
        combination=Combination(
            documents=[],
            document_refs={"persona": [str(d.document_id) for d in documents]},
        ),
        workflow_analysis_run_id=uuid4(),
        case_id=uuid4(),
        document_inputs=documents,
        knowledge_context=[],
        tokens={},
        compilation_repository=workflow_rule_compilation_repository,
        result_repository=workflow_rule_result_repository,
    )


async def test_execute__when_false_persists_skipped_with_metadata(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, compilation = _validation_rule(tenant_id)
    rule.when = '@persona.tipo_entidad == "empresa"'
    evaluator = _evaluator_for_when(
        rule,
        compilation,
        [_persona_doc("natural")],
        workflow_rule_compilation_repository,
        workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.SKIPPED))
    expect(result.output).to(equal(None))
    expect(result.evaluation_metadata["when"]).to(equal(rule.when))
    expect(result.evaluation_metadata["matched"]).to(equal(False))


async def test_execute__when_true_proceeds_with_evaluation(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, compilation = _validation_rule(tenant_id)
    rule.when = '@persona.tipo_entidad == "natural"'
    compilation.artifact = {
        "version": 1,
        "prompt": "check",
        "available_slugs": ["persona"],
        "tree": {"ref": "c1"},
        "sub_checks": [
            {
                "id": "c1",
                "description": "ci con formato",
                "inputs": ["@persona.ci"],
                "tokens": [],
                "knowledge_refs": [],
                "method": "FORMAT_CHECK",
                "params": {"regex": r"\d{5,8}"},
            }
        ],
        "knowledge_refs": [],
    }
    evaluator = _evaluator_for_when(
        rule,
        compilation,
        [_persona_doc("natural")],
        workflow_rule_compilation_repository,
        workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.SUCCESS))
    expect(result.output["passed"]).to(be_true)


async def test_execute__invalid_when_expression_persists_errored(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, compilation = _validation_rule(tenant_id)
    rule.when = "esto no es un predicado válido"
    evaluator = _evaluator_for_when(
        rule,
        compilation,
        [_persona_doc("natural")],
        workflow_rule_compilation_repository,
        workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.ERRORED))
    expect(result.error).to(contain("when"))


async def test_execute__when_with_unresolved_ref_persists_skipped(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, compilation = _validation_rule(tenant_id)
    rule.when = '@otro_doc.campo == "x"'
    evaluator = _evaluator_for_when(
        rule,
        compilation,
        [_persona_doc("natural")],
        workflow_rule_compilation_repository,
        workflow_rule_result_repository,
    )

    result = await evaluator.execute()

    expect(result.status).to(equal(WorkflowRuleResultStatus.SKIPPED))
    expect(result.evaluation_metadata["reason"]).to(contain("unresolved"))


# ---------- phases-config · H1 · kind_override (analyze.*_provider) ---------- #


class _RecordingKind:
    """Kind falso que registra la invocación — prueba que ``kind_override`` tiene
    precedencia sobre el ``registry`` global (overrides de provider por run)."""

    def __init__(self):
        self.calls = 0

    async def evaluate(self, rule, compilation, inputs, ctx):
        self.calls += 1
        return EvaluationOutcome(output={"passed": True}, reasoning="override-kind")


async def test_execute__kind_override_takes_precedence_over_registry(
    tenant_id,
    workflow_rule_compilation_repository,
    workflow_rule_result_repository,
):
    rule, compilation = _validation_rule(tenant_id)
    workflow_rule_compilation_repository.find_by_id.return_value = compilation
    workflow_rule_result_repository.upsert.side_effect = lambda r: r
    override = _RecordingKind()

    result = await WorkflowRuleEvaluator(
        rule=rule,
        combination=Combination(documents=[], document_refs={}),
        workflow_analysis_run_id=uuid4(),
        case_id=uuid4(),
        document_inputs=[],
        knowledge_context=[],
        tokens={},
        compilation_repository=workflow_rule_compilation_repository,
        result_repository=workflow_rule_result_repository,
        kind_override=override,
    ).execute()

    expect(override.calls).to(equal(1))
    expect(result.status).to(equal(WorkflowRuleResultStatus.SUCCESS))
    expect(result.reasoning).to(equal("override-kind"))
