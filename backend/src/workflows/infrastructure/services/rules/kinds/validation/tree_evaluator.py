"""Fold per-sub_check results into the final {passed, reason} pair via AND/OR/NOT."""

from __future__ import annotations

from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds.validation.dispatcher import (
    SubCheckResult,
)


def evaluate_tree(
    tree: dict[str, Any],
    sub_check_results: list[SubCheckResult],
) -> tuple[bool, str]:
    by_id = {r.sub_check_id: r for r in sub_check_results}
    passed, reason_parts = _eval_node(tree, by_id)
    reason = "; ".join(reason_parts) if reason_parts else ("All checks passed" if passed else "Tree failed")
    return passed, reason


def _eval_node(
    node: dict[str, Any],
    by_id: dict[str, SubCheckResult],
) -> tuple[bool, list[str]]:
    if "ref" in node:
        result = by_id.get(node["ref"])
        if result is None:
            msg = f"tree_evaluator: ref {node['ref']!r} has no sub_check result"
            raise InvalidWorkflowRuleConfigError(msg)
        return result.passed, [] if result.passed else [f"{result.sub_check_id}: {result.reason}"]
    op = node["op"]
    children = node["children"]
    if op == "AND":
        all_passed = True
        reasons: list[str] = []
        for child in children:
            child_passed, child_reasons = _eval_node(child, by_id)
            all_passed = all_passed and child_passed
            reasons.extend(child_reasons)
        return all_passed, reasons
    if op == "OR":
        any_passed = False
        reasons = []
        for child in children:
            child_passed, child_reasons = _eval_node(child, by_id)
            any_passed = any_passed or child_passed
            if not child_passed:
                reasons.extend(child_reasons)
        if any_passed:
            return True, []
        return False, reasons
    if op == "NOT":
        child_passed, child_reasons = _eval_node(children[0], by_id)
        if not child_passed:
            return True, []
        return False, [f"NOT-clause was true: {child_reasons or 'inner check passed'}"]
    msg = f"tree_evaluator: unknown op {op!r}"
    raise InvalidWorkflowRuleConfigError(msg)
