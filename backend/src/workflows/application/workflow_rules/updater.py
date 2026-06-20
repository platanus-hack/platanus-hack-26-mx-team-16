"""Update a WorkflowRule (spec §10.2). Detects invalidating edits."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import (
    InvalidWorkflowRuleConfigError,
    WorkflowRuleNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.application.workflow_rules.compilation.invalidation import (
    is_invalidating_change,
)
from src.workflows.application.workflow_rules.evaluation.when_evaluator import (
    parse_rule_when,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.kinds._shared.schema import (
    validate_against,
)


@dataclass
class WorkflowRuleUpdateOutcome:
    rule: WorkflowRule
    needs_recompilation: bool


@dataclass
class WorkflowRuleUpdater(UseCase):
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository
    name: str | None = None
    is_active: bool | None = None
    kind: str | None = None
    prompt: str | None = None
    config: dict[str, Any] | None = None
    scope: dict[str, Any] | None = None
    knowledge_refs: list[UUID] | None = None
    # E5 · None ⇒ untouched; "" ⇒ limpiar; cualquier otro string ⇒ validar y fijar.
    when: str | None = None

    async def execute(self) -> WorkflowRuleUpdateOutcome:
        existing = await self.rule_repository.find_by_id(self.rule_id, self.tenant_id)
        if not existing:
            raise WorkflowRuleNotFoundError(str(self.rule_id))

        snapshot_old = existing.model_copy(deep=True)

        if self.name is not None:
            if not self.name.strip():
                msg = "name is required"
                raise InvalidWorkflowRuleConfigError(msg)
            existing.name = self.name.strip()
        if self.is_active is not None:
            existing.is_active = self.is_active
        if self.kind is not None:
            existing.kind = self.kind
        if self.prompt is not None:
            if not self.prompt.strip():
                msg = "prompt is required"
                raise InvalidWorkflowRuleConfigError(msg)
            existing.prompt = self.prompt
        if self.config is not None:
            existing.config = self.config
        if self.scope is not None:
            existing.scope = self.scope
        if self.knowledge_refs is not None:
            existing.knowledge_refs = list(self.knowledge_refs)
        if self.when is not None:
            cleaned_when = self.when.strip() or None
            if cleaned_when:
                parse_rule_when(cleaned_when)
            # `when` es runtime-only: cambiarlo NO invalida la compilación
            # (no participa de compilation_input_hash).
            existing.when = cleaned_when

        kind = registry.get(existing.kind)
        validate_against(existing.config, kind.config_schema, label=f"{existing.kind}.config")

        needs = is_invalidating_change(snapshot_old, existing)
        updated = await self.rule_repository.update(existing)
        return WorkflowRuleUpdateOutcome(rule=updated, needs_recompilation=needs)
