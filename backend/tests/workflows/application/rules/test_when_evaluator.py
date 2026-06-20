"""Unit tests for the rule-level `when` predicate evaluator (E5)."""

from uuid import uuid4

import pytest
from expects import be_false, be_true, contain, equal, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.application.workflow_rules.evaluation.when_evaluator import (
    evaluate_rule_when,
    parse_rule_when,
)
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput


def _doc(slug: str, fields: dict) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug=slug,
        extracted_fields=fields,
    )


# ---------------- parse ---------------- #


@pytest.mark.parametrize(
    "expression",
    [
        '@persona.tipo_entidad == "natural"',
        "@persona.tipo_entidad != 'empresa'",
        "@{persona}.tipo_entidad == natural",
        "@factura.monto == 42",
        "@factura.monto != 3.14",
        "1 == 1",
    ],
)
def test_parse_rule_when__accepts_supported_grammar(expression):
    predicate = parse_rule_when(expression)
    expect(predicate.op in {"==", "!="}).to(be_true)


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "garbage",
        "@persona.tipo_entidad",
        "@persona.tipo_entidad >= 5",
        "@persona.tipo_entidad ==",
        "== natural",
        "@a.b == x == y",
    ],
)
def test_parse_rule_when__rejects_invalid_expressions(expression):
    with pytest.raises(InvalidWorkflowRuleConfigError):
        parse_rule_when(expression)


# ---------------- evaluate ---------------- #


def test_evaluate__equality_against_string_matches():
    docs = [_doc("persona", {"tipo_entidad": "natural"})]

    outcome = evaluate_rule_when('@persona.tipo_entidad == "natural"', docs)

    expect(outcome.matched).to(be_true)


def test_evaluate__equality_against_string_does_not_match():
    docs = [_doc("persona", {"tipo_entidad": "natural"})]

    outcome = evaluate_rule_when('@persona.tipo_entidad == "empresa"', docs)

    expect(outcome.matched).to(be_false)


def test_evaluate__inequality_is_strict_negation_of_equality():
    docs = [_doc("persona", {"tipo_entidad": "natural"})]

    expect(evaluate_rule_when('@persona.tipo_entidad != "empresa"', docs).matched).to(be_true)
    expect(evaluate_rule_when('@persona.tipo_entidad != "natural"', docs).matched).to(be_false)


def test_evaluate__numbers_compare_numerically_across_types():
    docs = [_doc("factura", {"monto": "42"})]

    expect(evaluate_rule_when("@factura.monto == 42", docs).matched).to(be_true)
    expect(evaluate_rule_when("@factura.monto == 42.0", docs).matched).to(be_true)
    expect(evaluate_rule_when("@factura.monto != 41", docs).matched).to(be_true)


def test_evaluate__bare_word_right_side_is_a_string_literal():
    docs = [_doc("persona", {"tipo_entidad": "empresa"})]

    expect(evaluate_rule_when("@persona.tipo_entidad == empresa", docs).matched).to(be_true)


def test_evaluate__unresolved_document_slug_does_not_match():
    docs = [_doc("factura", {"monto": 10})]

    outcome = evaluate_rule_when('@persona.tipo_entidad == "natural"', docs)

    expect(outcome.matched).to(be_false)
    expect(outcome.reason).to(contain("@persona.tipo_entidad"))


def test_evaluate__unresolved_field_does_not_match():
    docs = [_doc("persona", {"otro_campo": "x"})]

    outcome = evaluate_rule_when('@persona.tipo_entidad != "natural"', docs)

    # Even `!=` does not match on unresolved refs: the rule only applies
    # when the predicate is demonstrably true.
    expect(outcome.matched).to(be_false)
    expect(outcome.reason).to(contain("unresolved"))


def test_evaluate__matches_when_any_document_value_satisfies_equality():
    docs = [
        _doc("persona", {"tipo_entidad": "empresa"}),
        _doc("persona", {"tipo_entidad": "natural"}),
    ]

    outcome = evaluate_rule_when('@persona.tipo_entidad == "natural"', docs)

    expect(outcome.matched).to(be_true)


def test_evaluate__invalid_expression_raises():
    with pytest.raises(InvalidWorkflowRuleConfigError):
        evaluate_rule_when("@@nope", [_doc("persona", {"a": 1})])


def test_evaluate__reason_is_none_when_resolved():
    docs = [_doc("persona", {"tipo_entidad": "natural"})]

    outcome = evaluate_rule_when('@persona.tipo_entidad == "natural"', docs)

    expect(outcome.reason).to(equal(None))


def test_evaluate__quoted_literal_is_strict_string_no_numeric_coercion():
    # `'0123'` is quoted → it must compare as a string. A doc value of `"123"`
    # must NOT match because numeric coercion is disabled for quoted literals.
    docs = [_doc("doc", {"code": "123"})]

    expect(evaluate_rule_when("@doc.code == '0123'", docs).matched).to(be_false)
    expect(evaluate_rule_when("@doc.code != '0123'", docs).matched).to(be_true)


def test_evaluate__quoted_literal_matches_identical_string():
    docs = [_doc("doc", {"code": "0123"})]

    expect(evaluate_rule_when("@doc.code == '0123'", docs).matched).to(be_true)
