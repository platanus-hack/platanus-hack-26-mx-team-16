"""Pure-unit tests for the verdict aggregator (synthesis spec §4.2)."""

from uuid import uuid4

import pytest
from expects import contain, equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import (
    WorkflowRuleResultStatus,
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)
from src.common.domain.models.processing.verdict_signal import VerdictSignal
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.infrastructure.services.run_summary import verdict_logic


def _signal(
    *,
    rule_id=None,
    polarity=WorkflowRuleVerdictPolarity.PASS,
    severity=WorkflowRuleSeverity.MAJOR,
) -> VerdictSignal:
    return VerdictSignal(
        rule_id=rule_id or uuid4(),
        kind="VALIDATION",
        severity=severity,
        polarity=polarity,
    )


def _result(*, status=WorkflowRuleResultStatus.SUCCESS, rule_id=None) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=rule_id or uuid4(),
        case_id=uuid4(),
        kind="VALIDATION",
        status=status,
        document_refs_hash="hash",
    )


def test_aggregate__pass_when_only_pass_signals():
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[_result()],
    )

    expect(bundle.verdict).to(equal(Verdict.PASS))
    expect(bundle.blocking_failures).to(equal([]))


def test_aggregate__fail_when_blocker_failure():
    rule_id = uuid4()
    bundle = verdict_logic.aggregate(
        signals=[
            _signal(
                rule_id=rule_id,
                polarity=WorkflowRuleVerdictPolarity.FAIL,
                severity=WorkflowRuleSeverity.BLOCKER,
            )
        ],
        results=[_result(rule_id=rule_id)],
    )

    expect(bundle.verdict).to(equal(Verdict.FAIL))
    expect(bundle.blocking_failures).to(contain(rule_id))


def test_aggregate__review_when_non_blocker_failure():
    bundle = verdict_logic.aggregate(
        signals=[
            _signal(
                polarity=WorkflowRuleVerdictPolarity.FAIL,
                severity=WorkflowRuleSeverity.MAJOR,
            )
        ],
        results=[_result()],
    )

    expect(bundle.verdict).to(equal(Verdict.REVIEW))


def test_aggregate__review_when_no_decisive_signals():
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.NEUTRAL)],
        results=[_result()],
    )

    expect(bundle.verdict).to(equal(Verdict.REVIEW))


def test_aggregate__counts_signals_by_polarity_and_severity():
    bundle = verdict_logic.aggregate(
        signals=[
            _signal(polarity=WorkflowRuleVerdictPolarity.PASS, severity=WorkflowRuleSeverity.MAJOR),
            _signal(polarity=WorkflowRuleVerdictPolarity.NEUTRAL, severity=WorkflowRuleSeverity.INFO),
        ],
        results=[_result()],
    )

    expect(bundle.signals_by_polarity).to(equal({"PASS": 1, "NEUTRAL": 1}))
    expect(bundle.signals_by_severity).to(equal({"MAJOR": 1, "INFO": 1}))


def test_aggregate__degraded_results_listed_and_lower_confidence():
    rule_id = uuid4()
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(),
            _result(status=WorkflowRuleResultStatus.ERRORED, rule_id=rule_id),
        ],
    )

    expect(bundle.degraded_rules).to(contain(rule_id))
    expect(bundle.confidence_score).to(equal(0.5))


def test_aggregate__too_many_degraded_rules_force_review():
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(),
            _result(status=WorkflowRuleResultStatus.ERRORED),
            _result(status=WorkflowRuleResultStatus.ERRORED),
        ],
    )

    expect(bundle.verdict).to(equal(Verdict.REVIEW))


def test_aggregate__empty_results_yields_review_and_no_confidence():
    bundle = verdict_logic.aggregate(signals=[], results=[])

    expect(bundle.verdict).to(equal(Verdict.REVIEW))
    expect(bundle.confidence_score).to(equal(None))


# ---------------- SKIPPED is inert (E5 §6, C16) ---------------- #


def test_aggregate__skipped_results_are_not_degraded():
    skipped_id = uuid4()
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(),
            _result(status=WorkflowRuleResultStatus.SKIPPED, rule_id=skipped_id),
        ],
    )

    # SKIPPED ("no aplica") must not appear in degraded_rules.
    expect(bundle.degraded_rules).to(equal([]))


def test_aggregate__pass_even_when_most_rules_skipped():
    # All applicable rules pass; the rest legitimately SKIPPED (multi-country
    # when-gating). The run must still reach PASS with full confidence.
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(status=WorkflowRuleResultStatus.SUCCESS),
            _result(status=WorkflowRuleResultStatus.SKIPPED),
            _result(status=WorkflowRuleResultStatus.SKIPPED),
        ],
    )

    expect(bundle.verdict).to(equal(Verdict.PASS))
    expect(bundle.confidence_score).to(equal(1.0))


def test_aggregate__degraded_ratio_excludes_skipped():
    # 1 ERRORED out of {1 SUCCESS, 1 ERRORED} applicable = 0.5 ratio → REVIEW.
    # The two SKIPPED rules do NOT dilute the ratio back under threshold.
    errored_id = uuid4()
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(status=WorkflowRuleResultStatus.SUCCESS),
            _result(status=WorkflowRuleResultStatus.ERRORED, rule_id=errored_id),
            _result(status=WorkflowRuleResultStatus.SKIPPED),
            _result(status=WorkflowRuleResultStatus.SKIPPED),
        ],
    )

    expect(bundle.verdict).to(equal(Verdict.REVIEW))
    expect(bundle.degraded_rules).to(equal([errored_id]))


def test_aggregate__all_skipped_yields_none_confidence():
    bundle = verdict_logic.aggregate(
        signals=[_signal(polarity=WorkflowRuleVerdictPolarity.PASS)],
        results=[
            _result(status=WorkflowRuleResultStatus.SKIPPED),
            _result(status=WorkflowRuleResultStatus.SKIPPED),
        ],
    )

    expect(bundle.confidence_score).to(equal(None))
