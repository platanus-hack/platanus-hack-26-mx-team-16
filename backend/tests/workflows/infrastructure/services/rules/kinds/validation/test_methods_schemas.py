"""Unit tests for the per-method `params` JSON Schemas.

The PARSER's output is post-validated against these schemas so a hallucinated
sub_check with the wrong params shape never lands in the artifact. We
exercise both sides of each method (valid and invalid) and the catch-all
"unknown method" branch.
"""

import pytest
from expects import contain, equal, expect, raise_error

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds.validation.methods import (
    METHOD_SCHEMAS,
    known_methods,
    validate_params,
)


def test_known_methods__covers_documented_set():
    expect(known_methods()).to(
        equal(
            {
                "FORMAT_CHECK",
                "RANGE_CHECK",
                "DATE_CHECK",
                "CHECKSUM_CHECK",
                "CROSS_REF_CHECK",
                "AGGREGATE_CHECK",
                "LLM_CHECK",
            }
        )
    )


def test_method_schemas__keys_match_known_methods():
    expect(set(METHOD_SCHEMAS.keys())).to(equal(known_methods()))


def test_validate_params__rejects_unknown_method():
    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        validate_params("DOES_NOT_EXIST", {})
    expect(str(info.value)).to(contain("DOES_NOT_EXIST"))


@pytest.mark.parametrize(
    "method,params",
    [
        ("FORMAT_CHECK", {"regex": r"^\d+$"}),
        ("FORMAT_CHECK", {"regex": r"\d+", "flags": "i"}),
        ("RANGE_CHECK", {"min": 0}),
        ("RANGE_CHECK", {"min": 0, "max": 100, "inclusive": True}),
        ("RANGE_CHECK", {}),
        ("DATE_CHECK", {"after": "{{now}}"}),
        ("DATE_CHECK", {"before": "2030-01-01", "format": "%Y-%m-%d"}),
        ("CHECKSUM_CHECK", {"algorithm": "rut_chile_mod11"}),
        ("CROSS_REF_CHECK", {"against": "@{contract}.partes[].rut", "mode": "subset"}),
        ("CROSS_REF_CHECK", {"against": "kb_slug", "mode": "equal"}),
        ("CROSS_REF_CHECK", {"against": "x", "mode": "match_normalized"}),
        ("AGGREGATE_CHECK", {"op": "count", "over": "@{invoice}[]"}),
        ("AGGREGATE_CHECK", {"op": "sum", "over": "x", "predicate": {"any": "thing"}}),
        ("LLM_CHECK", {"question": "¿Pasa?"}),
        ("LLM_CHECK", {"question": "¿Pasa?", "criteria": "estricto"}),
    ],
)
def test_validate_params__accepts_valid_payloads(method, params):
    expect(lambda: validate_params(method, params)).not_to(raise_error(InvalidWorkflowRuleConfigError))


@pytest.mark.parametrize(
    "method,params,why",
    [
        ("FORMAT_CHECK", {}, "regex required"),
        ("FORMAT_CHECK", {"regex": ""}, "regex minLength"),
        ("RANGE_CHECK", {"min": True}, "min must be number/string/null"),
        ("CHECKSUM_CHECK", {}, "algorithm required"),
        ("CHECKSUM_CHECK", {"algorithm": ""}, "algorithm minLength"),
    ],
)
def test_validate_params__rejects_invalid_payloads(method, params, why):
    with pytest.raises(InvalidWorkflowRuleConfigError):
        validate_params(method, params)


@pytest.mark.parametrize(
    "method,params,reason",
    [
        ("RANGE_CHECK", {"min_exclusive": 0}, "RANGE with min_exclusive"),
        ("DATE_CHECK", {"min_age_years": 18, "reference": "{{now}}"}, "DATE with min_age_years"),
        ("DATE_CHECK", {"not_before": "{{now}}"}, "DATE with not_before"),
        ("AGGREGATE_CHECK", {"iterator": "@invoice[]", "predicate": "EXISTS"}, "AGGREGATE iterator/predicate"),
        (
            "AGGREGATE_CHECK",
            {
                "iterator": "@invoice[]",
                "predicate": "SUM_GT",
                "field": "monto_total",
                "value": 1_000_000,
                "filter": {"field": "moneda", "op": "=", "value": "CLP"},
            },
            "AGGREGATE SUM_GT shape",
        ),
        (
            "CROSS_REF_CHECK",
            {"lookup_in": "#comunas", "match_field": "@invoice.emisor.direccion.comuna"},
            "CROSS_REF lookup shape",
        ),
        (
            "CROSS_REF_CHECK",
            {
                "primary": "concat(@dni.nombres, ' ', @dni.apellidos)",
                "secondary_iterator": "@contract.partes[]",
                "secondary_field": "nombre",
                "normalize": ["lowercase", "strip_accents", "collapse_spaces"],
                "fallback_match": {"field": "rut", "value": "@dni.rut"},
            },
            "CROSS_REF normalize+fallback shape",
        ),
        ("LLM_CHECK", {"expected_values": ["CHILENA"]}, "LLM expected_values"),
        ("LLM_CHECK", {"requires_visual_context": True}, "LLM requires_visual_context"),
        ("LLM_CHECK", {"cite_from": "#marco_legal", "topic": "plazo"}, "LLM cite_from+topic"),
        ("LLM_CHECK", {}, "LLM no params"),
    ],
)
def test_validate_params__accepts_extended_param_shapes(method, params, reason):
    """Lock in that extended param shapes (iterator/predicate, min_age_years, …) pass validation."""
    expect(lambda: validate_params(method, params)).not_to(raise_error(InvalidWorkflowRuleConfigError))
