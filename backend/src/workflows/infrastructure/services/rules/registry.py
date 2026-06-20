"""Registry of WorkflowRuleKind plugins (spec §4.2).

Each kind self-registers at app bootstrap. Lookups by ``name`` raise
``UnknownWorkflowRuleKindError`` so callers don't accidentally fan in
runtime-typed strings.
"""

from __future__ import annotations

from src.common.domain.exceptions.workflow_rules import UnknownWorkflowRuleKindError
from src.workflows.domain.rules.kind_protocol import WorkflowRuleKind

_REGISTRY: dict[str, WorkflowRuleKind] = {}


def register(kind: WorkflowRuleKind) -> None:
    """Register a kind. Idempotent — re-registering the same name overwrites."""
    _REGISTRY[kind.name] = kind


def get(name: str) -> WorkflowRuleKind:
    if name not in _REGISTRY:
        raise UnknownWorkflowRuleKindError(name)
    return _REGISTRY[name]


def list_all() -> list[WorkflowRuleKind]:
    return list(_REGISTRY.values())


def has(name: str) -> bool:
    return name in _REGISTRY


def clear() -> None:
    """Test helper — reset the registry between tests that re-register."""
    _REGISTRY.clear()
