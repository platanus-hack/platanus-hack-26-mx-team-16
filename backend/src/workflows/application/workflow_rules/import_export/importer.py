"""Import workflow rules from an export envelope (spec §14)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.common.domain.exceptions.workflow_rules import (
    InvalidWorkflowRuleConfigError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.application.workflow_rules.creator import WorkflowRuleCreator
from src.workflows.application.workflow_rules.import_export.report import WorkflowRuleImportReport
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.infrastructure.services.rules import registry

from uuid import UUID


class ImportConflictStrategy(str, Enum):
    SKIP = "SKIP"
    OVERWRITE = "OVERWRITE"
    RENAME = "RENAME"
    FAIL = "FAIL"

    @classmethod
    def _missing_(cls, value: object) -> "ImportConflictStrategy | None":
        # Case-insensitive: el bundle FE manda 'overwrite' (diseño §4) y el
        # import de reglas manda 'OVERWRITE'. Ambos resuelven al mismo miembro.
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


_SUPPORTED_SCHEMA_VERSIONS = {"1.0"}


@dataclass
class WorkflowRulesImporter(UseCase):
    """Validate + apply an import envelope. Use ``dry_run=True`` for preview."""

    workflow_id: UUID
    tenant_id: UUID
    payload: dict[str, Any]
    strategy: ImportConflictStrategy
    workflow_repository: WorkflowRepository
    rule_repository: WorkflowRuleRepository
    document_type_repository: DocumentTypeRepository
    kb_document_repository: KBDocumentRepository
    dry_run: bool = False

    async def execute(self) -> WorkflowRuleImportReport:
        report = WorkflowRuleImportReport()

        if self.payload.get("schema_version") not in _SUPPORTED_SCHEMA_VERSIONS:
            report.failed += 1
            report.errors.append(f"unsupported schema_version: {self.payload.get('schema_version')!r}")
            return report

        rules_payload = self.payload.get("rules") or []

        existing = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        existing_by_name = {r.name: r for r in existing}

        doc_types = await self.document_type_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        uuid_by_slug = {dt.slug: dt.uuid for dt in doc_types if dt.slug}

        for raw in rules_payload:
            try:
                self._validate_payload_entry(raw)
                name = raw["name"]

                overwrite_target: WorkflowRule | None = None
                if name in existing_by_name:
                    if self.strategy == ImportConflictStrategy.SKIP:
                        report.skipped += 1
                        continue
                    if self.strategy == ImportConflictStrategy.FAIL:
                        report.errors.append(f"conflict: {name}")
                        report.failed += 1
                        return report
                    if self.strategy == ImportConflictStrategy.RENAME:
                        name = self._unique_name(name, existing_by_name)
                        raw = {**raw, "name": name}
                        report.renamed += 1
                    elif self.strategy == ImportConflictStrategy.OVERWRITE:
                        # Create-then-swap (bug nº5): NO borramos el original
                        # todavía. Si la resolución de refs falla más abajo, el
                        # original sigue intacto en vez de perderse para siempre.
                        overwrite_target = existing_by_name[name]

                # Puede lanzar InvalidWorkflowRuleConfigError (slug irresoluble)
                # ⇒ se captura abajo; con OVERWRITE el original aún no se tocó.
                resolved_scope = self._resolve_scope(raw.get("scope") or {}, uuid_by_slug, report)
                resolved_kb_refs = await self._resolve_kb_refs(raw.get("knowledge_refs_external") or [], report)

                if self.dry_run:
                    if name not in {r.name for r in existing} and name not in {
                        r["name"] for r in rules_payload[: rules_payload.index(raw)]
                    }:
                        report.created += 1
                    continue

                # Las refs resolvieron ⇒ ahora sí es seguro reemplazar. Borramos
                # el original justo antes de crear el reemplazo (el unique
                # ``(workflow_id, slug)`` exige liberar el slug para preservar
                # ``@rule.<slug>``).
                if overwrite_target is not None:
                    await self.rule_repository.delete(overwrite_target.uuid, self.tenant_id)
                    existing_by_name.pop(overwrite_target.name, None)
                    report.overwritten += 1

                await WorkflowRuleCreator(
                    tenant_id=self.tenant_id,
                    workflow_id=self.workflow_id,
                    name=name,
                    kind=raw["kind"],
                    prompt=raw["prompt"],
                    when=raw.get("when"),
                    config=raw.get("config") or {},
                    scope=resolved_scope,
                    knowledge_refs=resolved_kb_refs,
                    is_active=bool(raw.get("is_active", True)),
                    # Preserva @rule.<slug> de los output_schema exportados.
                    slug=raw.get("slug"),
                    rule_repository=self.rule_repository,
                    workflow_repository=self.workflow_repository,
                ).execute()
                report.created += 1
            except InvalidWorkflowRuleConfigError as exc:
                report.errors.append(str(exc.message))
                report.failed += 1
            except Exception as exc:
                report.errors.append(str(exc))
                report.failed += 1

        return report

    @staticmethod
    def _validate_payload_entry(raw: dict[str, Any]) -> None:
        for required in ("name", "kind", "prompt"):
            if not raw.get(required):
                msg = f"missing field: {required}"
                raise InvalidWorkflowRuleConfigError(msg)
        if not registry.has(raw["kind"]):
            msg = f"unknown kind: {raw['kind']}"
            raise InvalidWorkflowRuleConfigError(msg)

    @staticmethod
    def _unique_name(base: str, existing_by_name: dict[str, WorkflowRule]) -> str:
        i = 2
        while f"{base} ({i})" in existing_by_name:
            i += 1
        return f"{base} ({i})"

    def _resolve_scope(
        self,
        scope: dict[str, Any],
        uuid_by_slug: dict[str, UUID],
        report: WorkflowRuleImportReport,
    ) -> dict[str, Any]:
        resolved = dict(scope)
        slug = resolved.pop("document_type_slug", None)
        if slug:
            target = uuid_by_slug.get(slug)
            if target is None:
                report.unresolved_doc_type_slugs.append(slug)
                msg = f"unresolved document_type_slug: {slug}"
                raise InvalidWorkflowRuleConfigError(msg)
            resolved["document_type"] = str(target)
        slugs = resolved.pop("document_types_slugs", None)
        if slugs:
            uuids = []
            for slug in slugs:
                target = uuid_by_slug.get(slug)
                if target is None:
                    report.unresolved_doc_type_slugs.append(slug)
                    msg = f"unresolved document_type_slug: {slug}"
                    raise InvalidWorkflowRuleConfigError(msg)
                uuids.append(str(target))
            resolved["document_types"] = uuids
        return resolved

    async def _resolve_kb_refs(
        self,
        kb_external: list[dict[str, Any]],
        report: WorkflowRuleImportReport,
    ) -> list[UUID]:
        if not kb_external:
            return []
        kb_docs = await self.kb_document_repository.list_by_tenant(self.tenant_id)
        kb_by_slug = {kb.slug: kb for kb in kb_docs if kb.slug}
        kb_by_name = {kb.file_name: kb for kb in kb_docs}

        resolved: list[UUID] = []
        for entry in kb_external:
            # E6 · W4: el slug es el identificador portable (los tokens son
            # ``#kb_slug``); ``name`` queda como fallback para envelopes 1.0 viejos.
            slug = entry.get("slug")
            name = entry.get("name")
            kb = kb_by_slug.get(slug) if slug else None
            if kb is None and name:
                kb = kb_by_name.get(name)
            if kb is None:
                report.unresolved_kb_refs.append(slug or name or "")
                continue
            resolved.append(kb.uuid)
        return resolved
