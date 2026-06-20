"""Evaluate a rule's `when` predicate against the combination documents (E5).

This is the *rule-level* conditional evaluator, applied per document
combination at analysis time — unrelated to (and independent from) anything
in the pipeline-phase engine.

Grammar: ``<operand> ==|!= <operand>`` where each operand is one of:

- a ``@slug.path`` document ref (braced ``@{slug}.path`` also accepted),
  resolved against the case documents of the combination being evaluated;
- a quoted string (``'natural'`` / ``"natural"``);
- a number (``42``, ``3.14``);
- a bare word, treated as a string literal (``natural``).

Semantics (documented decision — see e5-design §6):

- ``==`` matches when ANY resolved left value equals ANY resolved right
  value; ``!=`` is its strict negation.
- Numbers compare numerically (``"42" == 42``); everything else compares
  as trimmed strings.
- An unresolvable ref (document type absent from the combination, missing
  field) makes the predicate NOT match → the rule result is ``SKIPPED``:
  a rule only applies when its `when` is demonstrably true.
- A syntactically invalid expression raises
  ``InvalidWorkflowRuleConfigError`` — rejected at rule create/update, and
  surfaced as ``ERRORED`` if a bad expression ever reaches evaluation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    MissingDocumentError,
    resolve as resolve_doc_ref,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import parse_doc_refs

_OPERAND = (
    r"(@\{?[a-z0-9][a-z0-9_-]*\}?(?:\.[A-Za-z_]\w*|\[\d*\])*"  # @slug.path / @{slug}.path
    r"|'[^']*'"
    r'|"[^"]*"'
    r"|[^\s!=]+)"  # bare word / number
)
_WHEN_RE = re.compile(rf"^\s*{_OPERAND}\s*(==|!=)\s*{_OPERAND}\s*$")


@dataclass(frozen=True)
class RuleWhenPredicate:
    left: str
    op: str  # "==" | "!="
    right: str


@dataclass(frozen=True)
class RuleWhenOutcome:
    matched: bool
    reason: str | None = None


def parse_rule_when(expression: str) -> RuleWhenPredicate:
    """Parse (and thereby validate) a `when` expression."""
    match = _WHEN_RE.match(expression or "")
    if not match:
        msg = (
            f"invalid `when` predicate {expression!r} — expected "
            "`<@slug.path | 'literal' | number> ==|!= <@slug.path | 'literal' | number>`"
        )
        raise InvalidWorkflowRuleConfigError(msg)
    left, op, right = match.group(1), match.group(2), match.group(3)
    return RuleWhenPredicate(left=left, op=op, right=right)


def evaluate_rule_when(
    expression: str,
    documents: list[EvalDocumentInput],
) -> RuleWhenOutcome:
    predicate = parse_rule_when(expression)
    left = _operand_values(predicate.left, documents)
    right = _operand_values(predicate.right, documents)
    if left is None:
        return RuleWhenOutcome(matched=False, reason=f"unresolved ref {predicate.left!r}")
    if right is None:
        return RuleWhenOutcome(matched=False, reason=f"unresolved ref {predicate.right!r}")
    any_equal = any(_values_equal(a, b) for a in left for b in right)
    matched = any_equal if predicate.op == "==" else not any_equal
    return RuleWhenOutcome(matched=matched)


@dataclass(frozen=True)
class _QuotedLiteral:
    """A string operand that was written with quotes — it must compare as a
    string and NEVER be coerced to a number, so `'0123' == '123'` is false."""

    value: str


def _operand_values(token: str, documents: list[EvalDocumentInput]) -> list | None:
    """Resolve one operand to its candidate values; None ⇒ unresolvable ref."""
    if token.startswith("@"):
        refs = parse_doc_refs(token)
        if not refs:
            return None
        try:
            resolved = resolve_doc_ref(refs[0], documents, required=False)
        except MissingDocumentError:
            return None
        values = [r.value for r in resolved if r.value is not None]
        return values or None
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
        return [_QuotedLiteral(token[1:-1])]
    return [token]


def _values_equal(a: object, b: object) -> bool:
    # A quoted literal forces a strict string comparison on both sides: numeric
    # coercion is disabled so leading-zero strings keep their identity.
    if isinstance(a, _QuotedLiteral) or isinstance(b, _QuotedLiteral):
        return _as_text(a).strip() == _as_text(b).strip()
    left_num, right_num = _as_number(a), _as_number(b)
    if left_num is not None and right_num is not None:
        return left_num == right_num
    return str(a).strip() == str(b).strip()


def _as_text(value: object) -> str:
    if isinstance(value, _QuotedLiteral):
        return value.value
    return str(value)


def _as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None
