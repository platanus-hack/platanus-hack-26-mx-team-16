"""Export workflow rules of a workflow to a portable JSON envelope (spec §14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository

EXPORT_SCHEMA_VERSION = "1.0"


@dataclass
class WorkflowRulesExporter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository
    document_type_repository: DocumentTypeRepository
    kb_document_repository: KBDocumentRepository

    async def execute(self) -> dict[str, Any]:
        rules = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        doc_types = await self.document_type_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        slug_by_uuid = {dt.uuid: dt.slug for dt in doc_types}

        exported_rules: list[dict[str, Any]] = []
        for rule in rules:
            scope = dict(rule.scope or {})
            self._replace_doc_type_uuid_with_slug(scope, "document_type", slug_by_uuid)
            self._replace_doc_type_uuid_list_with_slugs(scope, "document_types", slug_by_uuid)

            kb_refs_external: list[dict[str, Any]] = []
            for kb_id in rule.knowledge_refs or []:
                kb = await self.kb_document_repository.find_by_id(kb_id, self.tenant_id)
                if kb is not None:
                    # E6 · W4: los tokens de regla son ``#kb_slug`` ⇒ el slug es el
                    # identificador portable. ``name`` queda como fallback legible.
                    kb_refs_external.append({"slug": kb.slug, "name": kb.file_name})

            exported_rules.append(
                {
                    "name": rule.name,
                    "slug": rule.slug,
                    "kind": rule.kind,
                    "prompt": rule.prompt,
                    "when": rule.when,
                    "config": rule.config,
                    "scope": scope,
                    "knowledge_refs_external": kb_refs_external,
                    "position": rule.position,
                    "is_active": rule.is_active,
                }
            )

        return {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "exported_at": datetime.now(UTC).isoformat(),
            "source_workflow_id": str(self.workflow_id),
            "source_tenant_id": str(self.tenant_id),
            "rules": exported_rules,
        }

    @staticmethod
    def _replace_doc_type_uuid_with_slug(
        scope: dict[str, Any], key: str, slug_by_uuid: dict[UUID, str | None]
    ) -> None:
        value = scope.get(key)
        if not value:
            return
        try:
            uuid_value = UUID(str(value))
        except ValueError:
            return
        slug = slug_by_uuid.get(uuid_value)
        if slug:
            scope.pop(key, None)
            scope[f"{key}_slug"] = slug

    @staticmethod
    def _replace_doc_type_uuid_list_with_slugs(
        scope: dict[str, Any], key: str, slug_by_uuid: dict[UUID, str | None]
    ) -> None:
        values = scope.get(key)
        if not values:
            return
        slugs: list[str] = []
        for value in values:
            try:
                uuid_value = UUID(str(value))
            except ValueError:
                continue
            slug = slug_by_uuid.get(uuid_value)
            if slug:
                slugs.append(slug)
        if slugs:
            scope.pop(key, None)
            scope[f"{key}_slugs"] = slugs
