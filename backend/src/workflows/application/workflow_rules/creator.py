"""Create a WorkflowRule (spec §10.2)."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.exceptions.workflow_rules import (
    InvalidWorkflowRuleConfigError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.services.document_type_slug import compute_unique_slug
from src.workflows.domain.services.rule_slug import slugify_rule_name
from src.workflows.application.workflow_rules.evaluation.when_evaluator import (
    parse_rule_when,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.kinds._shared.schema import (
    validate_against,
)


@dataclass
class WorkflowRuleCreator(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    name: str
    kind: str
    prompt: str
    rule_repository: WorkflowRuleRepository
    workflow_repository: WorkflowRepository
    config: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=lambda: {"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"})
    knowledge_refs: list[UUID] = field(default_factory=list)
    is_active: bool = True
    # Slug explícito (import/export preserva @rule.<slug>); None ⇒ derivado del name.
    slug: str | None = None
    # E5 · predicado condicional (`@slug.path ==|!= <valor>`); None ⇒ aplica siempre.
    when: str | None = None

    async def execute(self) -> WorkflowRule:
        if not self.name or not self.name.strip():
            msg = "name is required"
            raise InvalidWorkflowRuleConfigError(msg)
        if not self.prompt or not self.prompt.strip():
            msg = "prompt is required"
            raise InvalidWorkflowRuleConfigError(msg)

        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))

        kind = registry.get(self.kind)
        config = {**kind.default_config(), **(self.config or {})}
        validate_against(config, kind.config_schema, label=f"{self.kind}.config")

        when = (self.when or "").strip() or None
        if when:
            parse_rule_when(when)  # raises InvalidWorkflowRuleConfigError on bad syntax

        siblings = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        existing_slugs = {r.slug for r in siblings if r.slug}
        base = slugify_rule_name(self.slug) if self.slug else slugify_rule_name(self.name)
        slug = compute_unique_slug(base, existing_slugs)

        rule = WorkflowRule(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=self.name.strip(),
            slug=slug,
            kind=self.kind,
            prompt=self.prompt,
            when=when,
            config=config,
            scope=self.scope,
            knowledge_refs=list(self.knowledge_refs or []),
            is_active=self.is_active,
        )
        return await self.rule_repository.create(rule)
