"""JSON-schema helpers shared by kinds (spec §4)."""

from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema.exceptions import SchemaError, ValidationError

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError


def assert_valid_schema(schema: dict[str, Any], *, label: str = "schema") -> None:
    """Raises InvalidWorkflowRuleConfigError if `schema` is not a valid JSON Schema."""
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        msg = f"{label}: {exc.message}"
        raise InvalidWorkflowRuleConfigError(msg) from exc


def validate_against(value: Any, schema: dict[str, Any], *, label: str = "value") -> None:
    try:
        jsonschema.validate(instance=value, schema=schema)
    except ValidationError as exc:
        msg = f"{label}: {exc.message}"
        raise InvalidWorkflowRuleConfigError(msg) from exc
