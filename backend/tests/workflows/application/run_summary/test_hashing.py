"""Tests for input_hash projection (synthesis spec §16.6)."""

from uuid import uuid4

from expects import equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash


def _result(
    *,
    output: dict | None = None,
    evaluation_metadata: dict | None = None,
    reasoning: str | None = None,
    rendered_prompt: str | None = None,
) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=uuid4(),
        case_id=uuid4(),
        kind="VALIDATION",
        status=WorkflowRuleResultStatus.SUCCESS,
        output=output or {"passed": True, "reason": "ok"},
        reasoning=reasoning,
        evaluation_metadata=evaluation_metadata or {},
        rendered_prompt=rendered_prompt,
        document_refs_hash="hash",
    )


def test_compute_input_hash__same_inputs_same_hash():
    rule_id = uuid4()
    a = WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=rule_id,
        case_id=uuid4(),
        kind="VALIDATION",
        output={"passed": True, "reason": "ok"},
        document_refs_hash="hash",
    )
    b = a.model_copy(update={"uuid": uuid4()})

    h1 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[a], output_schema=None, synthesis_template=None, model=None
    )
    h2 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[b], output_schema=None, synthesis_template=None, model=None
    )

    expect(h1).to(equal(h2))


def test_compute_input_hash__metadata_diff_does_not_change_hash():
    rule_id = uuid4()
    a = _result(
        output={"passed": True},
        evaluation_metadata={"raw_payload": "long llm reply v1"},
        reasoning="something",
        rendered_prompt="prompt v1",
    )
    a = a.model_copy(update={"rule_id": rule_id})
    b = a.model_copy(
        update={
            "rule_id": rule_id,
            "evaluation_metadata": {"raw_payload": "DIFFERENT llm reply"},
            "reasoning": "DIFFERENT",
            "rendered_prompt": "prompt v2",
        }
    )

    h1 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[a], output_schema=None, synthesis_template=None, model=None
    )
    h2 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[b], output_schema=None, synthesis_template=None, model=None
    )

    expect(h1).to(equal(h2))


def test_compute_input_hash__output_change_changes_hash():
    a = _result(output={"passed": True, "reason": "ok"})
    b = a.model_copy(update={"output": {"passed": False, "reason": "no"}})

    h1 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[a], output_schema=None, synthesis_template=None, model=None
    )
    h2 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[b], output_schema=None, synthesis_template=None, model=None
    )

    assert h1 != h2


def test_compute_input_hash__template_change_changes_hash():
    h1 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[], output_schema=None, synthesis_template="A", model=None
    )
    h2 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[], output_schema=None, synthesis_template="B", model=None
    )

    assert h1 != h2


def test_compute_input_hash__verdict_change_changes_hash():
    h1 = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[], output_schema=None, synthesis_template=None, model=None
    )
    h2 = compute_input_hash(
        verdict=Verdict.FAIL, rule_results=[], output_schema=None, synthesis_template=None, model=None
    )

    assert h1 != h2
