"""Sanity tests for ValidationKind / DerivationKind contracts (spec §5)."""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleResultStatus,
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation import ValidationKind


def _validation_rule() -> WorkflowRule:
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="check",
        config={"severity": "BLOCKER"},
    )


def _result(rule: WorkflowRule, *, output: dict | None) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=rule.tenant_id,
        workflow_analysis_run_id=uuid4(),
        rule_id=rule.uuid,
        case_id=uuid4(),
        kind=rule.kind,
        status=WorkflowRuleResultStatus.SUCCESS,
        output=output,
        document_refs_hash="hash",
    )


def test_validation_kind__contribute_pass_signal_when_passed():
    rule = _validation_rule()
    result = _result(rule, output={"passed": True, "reason": "ok"})

    signal = ValidationKind().contribute_to_verdict(rule, result)

    expect(signal.polarity).to(equal(WorkflowRuleVerdictPolarity.PASS))
    expect(signal.severity).to(equal(WorkflowRuleSeverity.BLOCKER))


def test_validation_kind__contribute_fail_signal_when_not_passed():
    rule = _validation_rule()
    result = _result(rule, output={"passed": False, "reason": "missing"})

    signal = ValidationKind().contribute_to_verdict(rule, result)

    expect(signal.polarity).to(equal(WorkflowRuleVerdictPolarity.FAIL))


def test_validation_kind__contribute_returns_none_for_errored_result():
    rule = _validation_rule()
    result = _result(rule, output=None)
    result.status = WorkflowRuleResultStatus.ERRORED

    signal = ValidationKind().contribute_to_verdict(rule, result)

    expect(signal).to(be_none)


def test_derivation_kind__never_contributes_to_verdict():
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="rule",
        kind="DERIVATION",
        prompt="extract",
        config={"output_shape": {"type": "object", "properties": {}}},
    )
    result = _result(rule, output={"any": "thing"})

    expect(DerivationKind().contribute_to_verdict(rule, result)).to(be_none)


@pytest.mark.parametrize(
    "passed,expected_polarity",
    [
        (True, WorkflowRuleVerdictPolarity.PASS),
        (False, WorkflowRuleVerdictPolarity.FAIL),
    ],
)
def test_validation_kind__polarity_table(passed, expected_polarity):
    rule = _validation_rule()
    result = _result(rule, output={"passed": passed, "reason": "x"})

    signal = ValidationKind().contribute_to_verdict(rule, result)

    expect(signal.polarity).to(equal(expected_polarity))
