"""Tests for the WorkflowRuleKind registry (spec §4.2)."""

import pytest
from expects import be, be_a, equal, expect

from src.common.domain.exceptions.workflow_rules import UnknownWorkflowRuleKindError
from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.bootstrap import register_default_kinds
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation import ValidationKind


@pytest.fixture(autouse=True)
def _isolated_registry():
    registry.clear()
    yield
    registry.clear()


def test_register__exposes_kind_via_get():
    kind = ValidationKind()

    registry.register(kind)

    expect(registry.get("VALIDATION")).to(be(kind))


def test_get__unknown_kind_raises():
    with pytest.raises(UnknownWorkflowRuleKindError):
        registry.get("NOPE")


def test_register_default_kinds__registers_validation_and_derivation():
    register_default_kinds()

    expect(registry.has("VALIDATION")).to(equal(True))
    expect(registry.has("DERIVATION")).to(equal(True))
    expect(registry.get("VALIDATION")).to(be_a(ValidationKind))
    expect(registry.get("DERIVATION")).to(be_a(DerivationKind))


def test_list_all__returns_registered_kinds():
    register_default_kinds()

    expect({k.name for k in registry.list_all()}).to(equal({"VALIDATION", "DERIVATION"}))


def test_register_default_kinds__is_idempotent():
    register_default_kinds()
    register_default_kinds()

    expect(len(registry.list_all())).to(equal(2))
