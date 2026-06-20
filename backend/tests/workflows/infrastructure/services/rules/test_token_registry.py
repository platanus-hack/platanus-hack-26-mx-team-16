"""Unit tests for the workflow `token_registry`."""

import pytest
from expects import equal, expect, raise_error

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.services import token_registry


@pytest.mark.parametrize(
    "token",
    ["now", "today", "today.year", "case.name", "tenant.name", "rule.severity"],
)
def test_assert_known__accepts_registered_tokens(token):
    expect(lambda: token_registry.assert_known([token], label="test")).not_to(
        raise_error(InvalidWorkflowRuleConfigError)
    )


def test_assert_known__rejects_unknown_token():
    expect(lambda: token_registry.assert_known(["foo.bar"], label="test")).to(
        raise_error(InvalidWorkflowRuleConfigError)
    )


def test_assert_known__error_lists_offending_tokens():
    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        token_registry.assert_known(["now", "unknown_one", "unknown_two"], label="prompt")
    message = str(info.value)
    expect("unknown_one" in message).to(equal(True))
    expect("unknown_two" in message).to(equal(True))
    expect("prompt" in message).to(equal(True))


def test_assert_known__empty_iterable_is_noop():
    expect(lambda: token_registry.assert_known([], label="test")).not_to(raise_error(InvalidWorkflowRuleConfigError))


def test_known_names__returns_at_least_baseline_tokens():
    known = token_registry.known_names()
    baseline = {"now", "today", "case.name", "tenant.name"}
    expect(baseline.issubset(known)).to(equal(True))


def test_is_known__matches_registry_membership():
    expect(token_registry.is_known("now")).to(equal(True))
    expect(token_registry.is_known("not_in_registry")).to(equal(False))


def test_get__returns_spec_for_registered_token():
    spec = token_registry.get("rule.severity")
    expect(spec.name).to(equal("rule.severity"))
    expect(spec.scope).to(equal("rule"))


def test_get__raises_for_unknown_token():
    expect(lambda: token_registry.get("does_not_exist")).to(raise_error(KeyError))


def test_known_for_scope__filters_by_scope():
    runtime_tokens = token_registry.known_for_scope("runtime")
    expect("now" in runtime_tokens).to(equal(True))
    expect("rule.severity" in runtime_tokens).to(equal(False))
