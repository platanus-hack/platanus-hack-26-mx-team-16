"""Unit tests for params substitution — bare `@slug.path` support (E5 fix)."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)
from src.workflows.infrastructure.services.rules.kinds._shared.substitution import (
    substitute,
)


def _resolved(value) -> list[ResolvedValue]:
    return [
        ResolvedValue(
            document_id=uuid4(),
            document_type_slug="dni",
            field_path="rut",
            value=value,
        )
    ]


def test_substitute__replaces_braced_ref_with_resolved_value():
    resolved = _resolved("12.345.678-5")

    out = substitute(
        {"against": "@{dni}.rut"},
        resolved_inputs={"@{dni}.rut": resolved},
        resolved_tokens={},
        sub_check_id="c1",
    )

    expect(out["against"]).to(equal(resolved))


def test_substitute__replaces_bare_ref_with_resolved_value():
    """The PARSER copies refs VERBATIM from prompts, i.e. mostly bare form."""
    resolved = _resolved("12.345.678-5")

    out = substitute(
        {"against": "@dni.rut"},
        resolved_inputs={"@dni.rut": resolved},
        resolved_tokens={},
        sub_check_id="c1",
    )

    expect(out["against"]).to(equal(resolved))


def test_substitute__replaces_bare_collection_ref():
    resolved = _resolved([{"nombre": "X"}])

    out = substitute(
        {"secondary_iterator": "@contract.partes[]"},
        resolved_inputs={"@contract.partes[]": resolved},
        resolved_tokens={},
        sub_check_id="c1",
    )

    expect(out["secondary_iterator"]).to(equal(resolved))


def test_substitute__leaves_embedded_refs_inside_expressions_untouched():
    out = substitute(
        {"primary": "concat(@dni.nombres, ' ', @dni.apellidos)"},
        resolved_inputs={},
        resolved_tokens={},
        sub_check_id="c1",
    )

    expect(out["primary"]).to(equal("concat(@dni.nombres, ' ', @dni.apellidos)"))


def test_substitute__undeclared_full_string_ref_raises():
    with pytest.raises(InvalidWorkflowRuleConfigError):
        substitute(
            {"against": "@dni.rut"},
            resolved_inputs={},
            resolved_tokens={},
            sub_check_id="c1",
        )
