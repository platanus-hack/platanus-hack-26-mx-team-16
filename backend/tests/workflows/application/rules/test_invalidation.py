"""Tests for compilation_input_hash + is_invalidating_change (spec §10.2)."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.application.workflow_rules.compilation.invalidation import (
    compilation_input_hash,
    is_invalidating_change,
)


def _build_rule(**overrides) -> WorkflowRule:
    base = dict(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="check it",
        config={"severity": "MAJOR"},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=[],
    )
    base.update(overrides)
    return WorkflowRule(**base)


def test_hash__same_inputs_produces_same_hash():
    a = _build_rule()
    b = _build_rule(uuid=a.uuid, tenant_id=a.tenant_id, workflow_id=a.workflow_id)

    expect(compilation_input_hash(a)).to(equal(compilation_input_hash(b)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("prompt", "different prompt"),
        ("kind", "DERIVATION"),
        ("scope", {"mode": "SINGLE_DOCUMENT", "document_type": str(uuid4())}),
    ],
)
def test_is_invalidating_change__true_for_invalidating_fields(field, value):
    old = _build_rule()
    new = old.model_copy(update={field: value})

    expect(is_invalidating_change(old, new)).to(equal(True))


def test_is_invalidating_change__detects_output_shape_change_within_config():
    old = _build_rule(kind="DERIVATION", config={"output_shape": {"type": "object"}})
    new = old.model_copy(
        update={"config": {"output_shape": {"type": "object", "properties": {"x": {"type": "string"}}}}}
    )

    expect(is_invalidating_change(old, new)).to(equal(True))


def test_is_invalidating_change__ignores_severity_change():
    old = _build_rule(config={"severity": "MAJOR"})
    new = old.model_copy(update={"config": {"severity": "BLOCKER"}})

    expect(is_invalidating_change(old, new)).to(equal(False))


def test_is_invalidating_change__ignores_name_position_active():
    old = _build_rule(name="old name", position=0, is_active=True)
    new = old.model_copy(update={"name": "new name", "position": 5, "is_active": False})

    expect(is_invalidating_change(old, new)).to(equal(False))


def test_is_invalidating_change__detects_knowledge_refs_change():
    old = _build_rule(knowledge_refs=[])
    new = old.model_copy(update={"knowledge_refs": [uuid4()]})

    expect(is_invalidating_change(old, new)).to(equal(True))
