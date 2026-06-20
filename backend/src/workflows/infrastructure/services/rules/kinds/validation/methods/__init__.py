"""JSON Schemas + helpers for the validation methods.

Each method has a permissive `params` JSON Schema. Compile only enforces the
core keys the dispatcher / downstream evaluators absolutely need (e.g.
FORMAT_CHECK requires a `regex`, CHECKSUM_CHECK requires an `algorithm`).
Everything else is left open via `additionalProperties: True` so PARSER
outputs that use shapes like `iterator`, `predicate`, `min_age_years`,
`lookup_in`, `requires_visual_context`, `fallback_match`, etc. survive
validation untouched.

The PARSER LLM is responsible for emitting params the runtime dispatcher
knows how to interpret; compile is intentionally lenient so new method
variants don't require a schema bump every time.
"""

from __future__ import annotations

from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.schema import (
    assert_valid_schema,
    validate_against,
)

FORMAT_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["regex"],
    "additionalProperties": True,
    "properties": {
        "regex": {"type": "string", "minLength": 1},
        "flags": {"type": "string"},
    },
}

RANGE_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "min": {"type": ["number", "string", "null"]},
        "max": {"type": ["number", "string", "null"]},
        "min_exclusive": {"type": ["number", "string", "null"]},
        "max_exclusive": {"type": ["number", "string", "null"]},
        "inclusive": {"type": "boolean"},
    },
}

DATE_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "before": {"type": ["string", "null"]},
        "after": {"type": ["string", "null"]},
        "not_before": {"type": ["string", "null"]},
        "not_after": {"type": ["string", "null"]},
        "min_age_years": {"type": ["integer", "number"]},
        "min_age_days": {"type": ["integer", "number"]},
        "max_age_years": {"type": ["integer", "number"]},
        "max_age_days": {"type": ["integer", "number"]},
        "reference": {"type": ["string", "null"]},
        "format": {"type": "string"},
    },
}

CHECKSUM_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["algorithm"],
    "additionalProperties": True,
    "properties": {
        "algorithm": {"type": "string", "minLength": 1},
    },
}

CROSS_REF_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "against": {"type": "string"},
        # Closed enum (E5 drift fix): compile rejects invented modes so the
        # artifact never carries a mode the dispatcher can't run. Runtime
        # additionally aliases legacy artifacts (exact/equals → equal,
        # match → match_normalized) in `handlers.cross_ref_check`.
        "mode": {"type": "string", "enum": ["equal", "subset", "match_normalized"]},
        "lookup_in": {"type": "string"},
        "match_field": {"type": "string"},
        "primary": {"type": "string"},
        "primary_iterator": {"type": "string"},
        "primary_field": {"type": "string"},
        "secondary_iterator": {"type": "string"},
        "secondary_field": {"type": "string"},
        "normalize": {"type": "array", "items": {"type": "string"}},
        "fallback_match": {"type": "object"},
        "filter": {"type": "object"},
        "secondary_filter": {"type": "object"},
        "predicate": {"type": ["string", "object"]},
    },
}

AGGREGATE_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "iterator": {"type": "string"},
        "over": {"type": "string"},
        "op": {"type": "string"},
        "predicate": {"type": ["string", "object"]},
        "expression": {"type": "string"},
        "conditions": {"type": "array"},
        "field": {"type": "string"},
        "value": {},
        "target": {"type": "string"},
        "tolerance": {"type": ["number", "integer"]},
        "filter": {"type": "object"},
    },
}

LLM_CHECK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "question": {"type": "string"},
        "criteria": {"type": "string"},
        "expected_values": {"type": "array"},
        "requires_visual_context": {"type": "boolean"},
        "cite_from": {"type": "string"},
        "topic": {"type": "string"},
        "context_lookup": {"type": "object"},
        "judgement": {"type": "string"},
    },
}


METHOD_SCHEMAS: dict[str, dict[str, Any]] = {
    "FORMAT_CHECK": FORMAT_CHECK_SCHEMA,
    "RANGE_CHECK": RANGE_CHECK_SCHEMA,
    "DATE_CHECK": DATE_CHECK_SCHEMA,
    "CHECKSUM_CHECK": CHECKSUM_CHECK_SCHEMA,
    "CROSS_REF_CHECK": CROSS_REF_CHECK_SCHEMA,
    "AGGREGATE_CHECK": AGGREGATE_CHECK_SCHEMA,
    "LLM_CHECK": LLM_CHECK_SCHEMA,
}


for _label, _schema in METHOD_SCHEMAS.items():
    assert_valid_schema(_schema, label=f"validation.method.{_label}")


def known_methods() -> set[str]:
    return set(METHOD_SCHEMAS.keys())


def validate_params(method: str, params: dict[str, Any]) -> None:
    schema = METHOD_SCHEMAS.get(method)
    if schema is None:
        msg = f"Unknown validation method: {method!r}. Known: {sorted(METHOD_SCHEMAS)}"
        raise InvalidWorkflowRuleConfigError(msg)
    validate_against(params, schema, label=f"validation.method.{method}.params")
