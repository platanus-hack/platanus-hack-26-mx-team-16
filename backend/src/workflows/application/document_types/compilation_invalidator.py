"""Invalidate rule compilations when a document type's contract changes (D6').

What triggers recompilation of a workflow rule today:

1. **Rule edits** — ``WorkflowRuleUpdater`` hashes the rule's own invalidating
   fields (prompt, kind, config.output_shape, scope, knowledge_refs); on a
   hash change the endpoint marks the current compilation ``STALE`` and
   schedules ``schedule_and_run_compilation`` in the background.
2. **Document type versions (this module)** — when ``DocumentTypeUpdater``
   creates a new immutable ``document_type_version`` (fields or
   validation_rules changed), the update endpoint runs this use case: every
   rule of the doc type's workflow that references it gets its current
   compilation marked ``STALE`` and is returned so the caller can schedule
   the same background recompilation flow.

A rule "references" the doc type when any of these holds:

- its ``scope`` mentions the doc type **uuid** (scope stores UUIDs, see
  ``scope_resolver``);
- its prompt contains an ``@slug`` doc ref for the doc type's slug
  (``parse_doc_refs`` — same parser used at compile time);
- the compiled **artifact** of its current compilation mentions the slug
  (derivation targets store ``{"doctype": slug}``; legacy ``{"slug": ...}``).

Rules without a current compilation are skipped — there is nothing to
invalidate and the normal create/update flow compiles them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import parse_doc_refs

logger = get_logger(__name__)

_ARTIFACT_SLUG_KEYS = ("doctype", "slug", "document_type_slug")


def _artifact_mentions_slug(value: Any, slug: str) -> bool:
    """Recursively look for ``{doctype|slug|document_type_slug: <slug>}``."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _ARTIFACT_SLUG_KEYS and item == slug:
                return True
            if _artifact_mentions_slug(item, slug):
                return True
        return False
    if isinstance(value, list):
        return any(_artifact_mentions_slug(item, slug) for item in value)
    return False


@dataclass
class DocumentTypeCompilationInvalidator(UseCase):
    """Mark STALE the compilations of rules referencing a doc type."""

    workflow_id: UUID
    tenant_id: UUID
    document_type_id: UUID
    document_type_slug: str | None
    rule_repository: WorkflowRuleRepository
    compilation_repository: WorkflowRuleCompilationRepository
    _doctype_uuid_str: str = field(init=False, default="")

    async def execute(self) -> list[WorkflowRule]:
        self._doctype_uuid_str = str(self.document_type_id)
        rules = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)

        invalidated: list[WorkflowRule] = []
        for rule in rules:
            if rule.current_compilation_id is None:
                continue
            if not await self._references_doc_type(rule):
                continue
            await self.compilation_repository.mark_status(
                rule.current_compilation_id,
                WorkflowRuleCompilationStatus.STALE,
            )
            invalidated.append(rule)

        if invalidated:
            logger.info(
                "document_type.compilations_invalidated "
                f"document_type_id={self.document_type_id} workflow_id={self.workflow_id} "
                f"rule_ids={[str(r.uuid) for r in invalidated]}"
            )
        return invalidated

    async def _references_doc_type(self, rule: WorkflowRule) -> bool:
        if self._scope_mentions_uuid(rule.scope):
            return True
        if self._prompt_mentions_slug(rule.prompt):
            return True
        return await self._artifact_mentions(rule)

    def _scope_mentions_uuid(self, scope: dict[str, Any] | None) -> bool:
        if not scope:
            return False
        return self._doctype_uuid_str in json.dumps(scope, default=str)

    def _prompt_mentions_slug(self, prompt: str | None) -> bool:
        if not prompt or not self.document_type_slug:
            return False
        return any(ref.slug == self.document_type_slug for ref in parse_doc_refs(prompt))

    async def _artifact_mentions(self, rule: WorkflowRule) -> bool:
        if not self.document_type_slug or rule.current_compilation_id is None:
            return False
        compilation = await self.compilation_repository.find_by_id(rule.current_compilation_id)
        if compilation is None or not compilation.artifact:
            return False
        return _artifact_mentions_slug(compilation.artifact, self.document_type_slug)
