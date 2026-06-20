"""Regression tests for the deterministic VALIDATION handlers' advertised params.

These params (`min_exclusive`, `min_age_years`, `not_before`, AGGREGATE
`value`/`target`/`tolerance`/`iterator`) were announced by the PARSER prompt and
the method schemas but IGNORED by the handlers — so a "mayor de edad" or
"> 0" rule compiled green and ALWAYS passed (C14/C15). Each param now has a
pass + fail case, including the boundary cases the fix must get right.
"""

from datetime import date
from uuid import uuid4

import pytest
from expects import be_false, be_true, contain, equal, expect, raise_error

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)
from src.workflows.infrastructure.services.rules.kinds.validation.methods.handlers import (
    aggregate_check,
    date_check,
    range_check,
)


def _rv(value) -> ResolvedValue:
    return ResolvedValue(document_id=uuid4(), document_type_slug="doc", field_path="f", value=value)


# ---------------- RANGE_CHECK min_exclusive / max_exclusive (C14) ---------------- #


def test_range_check__min_exclusive_rejects_value_at_bound():
    passed, _ = range_check([_rv(18)], {"min_exclusive": 18})
    expect(passed).to(be_false)


def test_range_check__min_exclusive_accepts_value_above_bound():
    passed, _ = range_check([_rv(19)], {"min_exclusive": 18})
    expect(passed).to(be_true)


def test_range_check__max_exclusive_rejects_value_at_bound():
    passed, _ = range_check([_rv(100)], {"max_exclusive": 100})
    expect(passed).to(be_false)


def test_range_check__min_exclusive_zero_rejects_zero():
    # The canonical "monto > 0" rule: 0 must FAIL, not silently PASS.
    passed, _ = range_check([_rv(0)], {"min_exclusive": 0})
    expect(passed).to(be_false)


def test_range_check__min_exclusive_zero_accepts_positive():
    passed, _ = range_check([_rv("0.01")], {"min_exclusive": 0})
    expect(passed).to(be_true)


# ---------------- DATE_CHECK min_age / not_before (C14) ---------------- #


def test_date_check__min_age_years_minor_fails():
    # Born 2010-06-10, reference 2026-06-10 → 16 years old < 18.
    passed, _ = date_check([_rv("2010-06-10")], {"min_age_years": 18, "reference": "2026-06-10"})
    expect(passed).to(be_false)


def test_date_check__min_age_years_adult_passes():
    passed, _ = date_check([_rv("2000-01-01")], {"min_age_years": 18, "reference": "2026-06-10"})
    expect(passed).to(be_true)


def test_date_check__min_age_years_turns_18_exactly_on_reference_day_passes():
    # Boundary: born exactly 18*365 days before the reference must PASS.
    born = date(2008, 6, 10)
    reference = date(born.year + 18, born.month, born.day)
    passed, _ = date_check(
        [_rv(born.isoformat())],
        {"min_age_years": 18, "reference": reference.isoformat()},
    )
    expect(passed).to(be_true)


def test_date_check__min_age_days_below_fails():
    passed, _ = date_check([_rv("2026-06-09")], {"min_age_days": 30, "reference": "2026-06-10"})
    expect(passed).to(be_false)


def test_date_check__not_before_inclusive_bound_passes():
    passed, _ = date_check([_rv("2026-01-01")], {"not_before": "2026-01-01"})
    expect(passed).to(be_true)


def test_date_check__not_before_earlier_value_fails():
    passed, _ = date_check([_rv("2025-12-31")], {"not_before": "2026-01-01"})
    expect(passed).to(be_false)


def test_date_check__not_after_later_value_fails():
    passed, _ = date_check([_rv("2026-02-01")], {"not_after": "2026-01-01"})
    expect(passed).to(be_false)


def test_date_check__reference_defaults_to_today_when_absent():
    # An impossible future birthdate can never satisfy min_age against "today".
    passed, _ = date_check([_rv("2030-01-01")], {"min_age_years": 18})
    expect(passed).to(be_false)


# ---------------- AGGREGATE_CHECK target/value/tolerance/iterator (C15) ---------------- #


def test_aggregate_check__count_with_value_target_pass():
    passed, _ = aggregate_check([], {"over": [_rv(1), _rv(2)], "op": "count", "value": 2})
    expect(passed).to(be_true)


def test_aggregate_check__count_with_value_target_fail():
    # Previously `value` was ignored → unconditional PASS. Now it must FAIL.
    passed, _ = aggregate_check([], {"over": [_rv(1), _rv(2)], "op": "count", "value": 5})
    expect(passed).to(be_false)


def test_aggregate_check__target_string_is_compared():
    passed, _ = aggregate_check([], {"over": [_rv(1), _rv(2)], "op": "count", "target": "5"})
    expect(passed).to(be_false)


def test_aggregate_check__predicate_equals_pass():
    passed, _ = aggregate_check(
        [], {"over": [_rv(10), _rv(20)], "op": "sum", "predicate": {"equals": 30}}
    )
    expect(passed).to(be_true)


def test_aggregate_check__tolerance_absorbs_small_delta():
    passed, _ = aggregate_check(
        [], {"over": [_rv(10), _rv(21)], "op": "sum", "value": 30, "tolerance": 1}
    )
    expect(passed).to(be_true)


def test_aggregate_check__tolerance_does_not_absorb_large_delta():
    passed, _ = aggregate_check(
        [], {"over": [_rv(10), _rv(25)], "op": "sum", "value": 30, "tolerance": 1}
    )
    expect(passed).to(be_false)


def test_aggregate_check__iterator_spelling_accepted():
    passed, _ = aggregate_check([], {"iterator": [_rv(1), _rv(2), _rv(3)], "op": "count", "value": 3})
    expect(passed).to(be_true)


def test_aggregate_check__missing_collection_is_config_error():
    expect(lambda: aggregate_check([], {"op": "count", "value": 1})).to(
        raise_error(InvalidWorkflowRuleConfigError)
    )


def test_aggregate_check__no_target_returns_actual_pass():
    passed, reason = aggregate_check([], {"over": [_rv(1), _rv(2)], "op": "count"})
    expect(passed).to(be_true)
    expect(reason).to(contain("2"))


def test_aggregate_check__conditions_all_rows_must_match():
    rows = [_rv({"cantidad": 2, "precio": 10}), _rv({"cantidad": 1, "precio": 5})]
    passed, _ = aggregate_check(
        [],
        {
            "over": rows,
            "predicate": "ALL",
            "conditions": [{"field": "cantidad", "op": ">", "value": 0}],
        },
    )
    expect(passed).to(be_true)


def test_aggregate_check__conditions_all_fails_when_a_row_violates():
    rows = [_rv({"cantidad": 2}), _rv({"cantidad": 0})]
    passed, _ = aggregate_check(
        [],
        {
            "over": rows,
            "predicate": "ALL",
            "conditions": [{"field": "cantidad", "op": ">", "value": 0}],
        },
    )
    expect(passed).to(be_false)


def test_aggregate_check__unknown_op_is_config_error():
    expect(
        lambda: aggregate_check([], {"over": [_rv(1)], "op": "median", "value": 1})
    ).to(raise_error(InvalidWorkflowRuleConfigError))
