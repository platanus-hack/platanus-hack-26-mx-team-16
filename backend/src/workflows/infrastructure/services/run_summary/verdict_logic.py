"""Pure functions that turn `VerdictSignal`s + degraded results into the verdict struct.

The verdict layer is auditable and reproducible: byte-perfect for the same
inputs. No LLM, no I/O. Mirrors synthesis spec §4.2 line by line.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import (
    WorkflowRuleResultStatus,
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)
from src.common.domain.models.processing.verdict_signal import VerdictSignal
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    SignalSnapshot,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult


@dataclass(frozen=True)
class VerdictBundle:
    verdict: Verdict
    signals: list[SignalSnapshot]
    signals_by_polarity: dict[str, int]
    signals_by_severity: dict[str, int]
    blocking_failures: list[UUID]
    degraded_rules: list[UUID]
    confidence_score: float | None


def aggregate(
    *,
    signals: Iterable[VerdictSignal],
    results: Iterable[WorkflowRuleResult],
    degraded_threshold: float = 0.5,
) -> VerdictBundle:
    signals_list = list(signals)
    results_list = list(results)

    snapshots = [_to_snapshot(s) for s in signals_list]
    signals_by_polarity = _count_by(s.polarity for s in snapshots)
    signals_by_severity = _count_by(s.severity for s in snapshots)

    blocking_failures = [
        s.rule_id
        for s in signals_list
        if s.polarity == WorkflowRuleVerdictPolarity.FAIL and s.severity == WorkflowRuleSeverity.BLOCKER
    ]
    # SKIPPED (rule did not apply per its `when`) is NOT degraded: per E5 design
    # §6 it "no afecta verdict ni blocking". Only ERRORED rules count as degraded.
    degraded_rules = [r.rule_id for r in results_list if r.status == WorkflowRuleResultStatus.ERRORED]

    verdict = _decide_verdict(
        signals=signals_list,
        results=results_list,
        blocking_failures=blocking_failures,
        degraded_rules=degraded_rules,
        degraded_threshold=degraded_threshold,
    )

    return VerdictBundle(
        verdict=verdict,
        signals=snapshots,
        signals_by_polarity=signals_by_polarity,
        signals_by_severity=signals_by_severity,
        blocking_failures=blocking_failures,
        degraded_rules=degraded_rules,
        confidence_score=_confidence_score(results_list),
    )


def _decide_verdict(
    *,
    signals: list[VerdictSignal],
    results: list[WorkflowRuleResult],
    blocking_failures: list[UUID],
    degraded_rules: list[UUID],
    degraded_threshold: float,
) -> Verdict:
    if blocking_failures:
        return Verdict.FAIL
    has_non_blocker_fails = any(
        s.polarity == WorkflowRuleVerdictPolarity.FAIL and s.severity != WorkflowRuleSeverity.BLOCKER for s in signals
    )
    if has_non_blocker_fails:
        return Verdict.REVIEW
    # No verdict-bearing signals at all — REVIEW (can't decide).
    has_decisive_signal = any(
        s.polarity in {WorkflowRuleVerdictPolarity.PASS, WorkflowRuleVerdictPolarity.FAIL} for s in signals
    )
    if not has_decisive_signal:
        return Verdict.REVIEW
    # Too many degraded rules → REVIEW. The ratio is over APPLICABLE results
    # only: SKIPPED rules ("no aplica" per their `when`) are excluded so a
    # multi-country workflow where ~half the rules legitimately skip can still
    # reach PASS (E5 design §6).
    applicable = [r for r in results if r.status != WorkflowRuleResultStatus.SKIPPED]
    if applicable and (len(degraded_rules) / len(applicable)) >= degraded_threshold:
        return Verdict.REVIEW
    return Verdict.PASS


def _confidence_score(results: list[WorkflowRuleResult]) -> float | None:
    # SKIPPED rules are excluded from the denominator: a rule that did not apply
    # neither helps nor hurts confidence. None when every rule was SKIPPED.
    applicable = [r for r in results if r.status != WorkflowRuleResultStatus.SKIPPED]
    if not applicable:
        return None
    successful = sum(1 for r in applicable if r.status == WorkflowRuleResultStatus.SUCCESS)
    return round(successful / len(applicable), 4)


def _count_by(values: Iterable[str]) -> dict[str, int]:
    counter: Counter[str] = Counter(str(v) for v in values)
    return dict(counter)


def _to_snapshot(signal: VerdictSignal) -> SignalSnapshot:
    return SignalSnapshot(
        rule_id=signal.rule_id,
        kind=signal.kind,
        severity=signal.severity.value,
        polarity=signal.polarity.value,
        weight=signal.weight,
        detail=dict(signal.detail or {}),
    )
