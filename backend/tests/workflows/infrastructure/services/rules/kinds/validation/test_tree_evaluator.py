"""Unit tests for evaluate_tree — AND/OR/NOT folding over SubCheckResults."""

from expects import be_false, be_true, equal, expect, raise_error

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds.validation.dispatcher import (
    SubCheckResult,
)
from src.workflows.infrastructure.services.rules.kinds.validation.tree_evaluator import (
    evaluate_tree,
)


def _ok(name: str) -> SubCheckResult:
    return SubCheckResult(sub_check_id=name, passed=True, reason="ok", citations=[])


def _ko(name: str, reason: str = "fail") -> SubCheckResult:
    return SubCheckResult(sub_check_id=name, passed=False, reason=reason, citations=[])


def test_evaluate_tree__leaf_ref_passes():
    tree = {"ref": "c1"}

    passed, _ = evaluate_tree(tree, [_ok("c1")])

    expect(passed).to(be_true)


def test_evaluate_tree__leaf_ref_fails_records_reason():
    tree = {"ref": "c1"}

    passed, reason = evaluate_tree(tree, [_ko("c1", "bad value")])

    expect(passed).to(be_false)
    expect(reason).to(equal("c1: bad value"))


def test_evaluate_tree__and_passes_when_all_pass():
    tree = {"op": "AND", "children": [{"ref": "c1"}, {"ref": "c2"}]}

    passed, _ = evaluate_tree(tree, [_ok("c1"), _ok("c2")])

    expect(passed).to(be_true)


def test_evaluate_tree__and_fails_when_any_fails():
    tree = {"op": "AND", "children": [{"ref": "c1"}, {"ref": "c2"}]}

    passed, reason = evaluate_tree(tree, [_ok("c1"), _ko("c2", "no")])

    expect(passed).to(be_false)
    expect(reason).to(equal("c2: no"))


def test_evaluate_tree__or_passes_when_any_passes():
    tree = {"op": "OR", "children": [{"ref": "c1"}, {"ref": "c2"}]}

    passed, _ = evaluate_tree(tree, [_ko("c1"), _ok("c2")])

    expect(passed).to(be_true)


def test_evaluate_tree__or_fails_when_all_fail_collects_reasons():
    tree = {"op": "OR", "children": [{"ref": "c1"}, {"ref": "c2"}]}

    passed, reason = evaluate_tree(tree, [_ko("c1", "x"), _ko("c2", "y")])

    expect(passed).to(be_false)
    expect("c1: x" in reason and "c2: y" in reason).to(be_true)


def test_evaluate_tree__not_inverts_inner_result():
    tree = {"op": "NOT", "children": [{"ref": "c1"}]}

    passed, _ = evaluate_tree(tree, [_ko("c1")])

    expect(passed).to(be_true)


def test_evaluate_tree__not_fails_when_inner_passes():
    tree = {"op": "NOT", "children": [{"ref": "c1"}]}

    passed, _ = evaluate_tree(tree, [_ok("c1")])

    expect(passed).to(be_false)


def test_evaluate_tree__nested_and_or():
    tree = {
        "op": "AND",
        "children": [
            {"ref": "c1"},
            {"op": "OR", "children": [{"ref": "c2"}, {"ref": "c3"}]},
        ],
    }

    passed, _ = evaluate_tree(tree, [_ok("c1"), _ko("c2"), _ok("c3")])

    expect(passed).to(be_true)


def test_evaluate_tree__missing_ref_raises():
    tree = {"ref": "missing"}

    expect(lambda: evaluate_tree(tree, [_ok("c1")])).to(raise_error(InvalidWorkflowRuleConfigError))


def test_evaluate_tree__unknown_op_raises():
    tree = {"op": "XOR", "children": [{"ref": "c1"}]}

    expect(lambda: evaluate_tree(tree, [_ok("c1")])).to(raise_error(InvalidWorkflowRuleConfigError))
