"""Unit tests for token_registry helpers."""

import pytest
from expects import contain, equal, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.services import token_registry


def test_parse_tokens__deduplicates_and_preserves_order():
    result = token_registry.parse_tokens("hi {{a}} {{b}} and {{a}} again")

    expect(result).to(equal(["a", "b"]))


def test_parse_tokens__supports_dotted_names():
    result = token_registry.parse_tokens("year={{today.year}} run={{run.id}}")

    expect(result).to(equal(["today.year", "run.id"]))


def test_parse_tokens__no_tokens_returns_empty():
    expect(token_registry.parse_tokens("nothing here")).to(equal([]))


def test_assert_known__accepts_registered_tokens():
    token_registry.assert_known(["now", "today.year", "run.id"])  # no raise


def test_assert_known__raises_with_label_for_unknown():
    with pytest.raises(InvalidWorkflowRuleConfigError, match="VALIDATION prompt"):
        token_registry.assert_known(["typo"], label="VALIDATION prompt")


def test_known_names__contains_run_scope_tokens():
    expect(token_registry.known_names()).to(contain("run.id"))
    expect(token_registry.known_names()).to(contain("run.completed_at"))
