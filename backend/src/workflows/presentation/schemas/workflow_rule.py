"""Request schemas for workflow-rule endpoints (spec §11)."""

from typing import Any
from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class CreateWorkflowRuleRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)
    kind: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=lambda: {"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"})
    knowledge_refs: list[UUID] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    # E5 · conditional rule predicate (`@slug.path ==|!= <valor>`); None ⇒ always applies.
    when: str | None = Field(default=None)


class UpdateWorkflowRuleRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    kind: str | None = Field(default=None, min_length=1, max_length=64)
    prompt: str | None = Field(default=None, min_length=1)
    config: dict[str, Any] | None = Field(default=None)
    scope: dict[str, Any] | None = Field(default=None)
    knowledge_refs: list[UUID] | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    # E5 · None ⇒ untouched; "" (cadena vacía) ⇒ limpiar el predicado.
    when: str | None = Field(default=None)


class ReorderWorkflowRulesRequest(CamelCaseRequest):
    rule_ids: list[UUID] = Field(..., min_length=1)


class ImportWorkflowRulesRequest(CamelCaseRequest):
    payload: dict[str, Any] = Field(...)
