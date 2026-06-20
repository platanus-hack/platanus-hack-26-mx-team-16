"""Import document types from a bundle section (E6 · W4).

Find-or-create by ``slug`` within the destination workflow:

* slug absent  ⇒ create (with a sealed v1, mirroring :class:`DocumentTypeCreator`).
* slug present ⇒ ``SKIP`` (default) leaves it untouched; ``OVERWRITE`` rewrites
  ``fields``/``validation_rules``/metadata and seals a NEW immutable version only
  when the schema actually differs (the version mechanism already exists, D6').

Returns a small report so the bundle importer can aggregate per-section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)
from src.workflows.domain.services.json_schema_validator import (
    validate_document_type_json_schema,
)
from src.workflows.domain.services.validation_rules_validator import (
    validate_document_type_validation_rules,
)


@dataclass
class DocumentTypeImportReport:
    created: int = 0
    overwritten: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    # slug entrante -> slug resuelto en destino (las reglas se resuelven contra estos)
    slug_map: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowDocumentTypesImporter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    payload: list[dict[str, Any]]
    strategy: ImportConflictStrategy
    document_type_repository: DocumentTypeRepository
    dry_run: bool = False

    async def execute(self) -> DocumentTypeImportReport:
        report = DocumentTypeImportReport()

        existing = await self.document_type_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        existing_by_slug = {dt.slug: dt for dt in existing if dt.slug}
        existing_slugs = {dt.slug for dt in existing if dt.slug}

        for raw in self.payload:
            try:
                name = (raw.get("name") or "").strip()
                if not name:
                    raise ValueError("document type missing required field: name")

                incoming_slug = (raw.get("slug") or "").strip() or None
                fields = raw.get("fields")
                if fields is not None:
                    validate_document_type_json_schema(fields)
                validation_rules = (
                    validate_document_type_validation_rules(raw.get("validation_rules"))
                    if raw.get("validation_rules") is not None
                    else []
                )

                match = existing_by_slug.get(incoming_slug) if incoming_slug else None

                if match is not None:
                    if self.strategy == ImportConflictStrategy.SKIP:
                        report.skipped += 1
                        report.slug_map[incoming_slug] = match.slug
                        continue
                    if self.strategy == ImportConflictStrategy.FAIL:
                        raise ValueError(f"document type conflict: {incoming_slug}")
                    # RENAME y OVERWRITE: OVERWRITE reescribe; RENAME crea nuevo.
                    if self.strategy == ImportConflictStrategy.OVERWRITE:
                        report.slug_map[incoming_slug] = match.slug
                        report.overwritten += 1
                        if not self.dry_run:
                            await self._overwrite(match, name, raw, fields, validation_rules)
                        continue

                # Create path (no match, or RENAME forces a fresh slug).
                base = slugify_doctype_name(incoming_slug or name)
                slug = compute_unique_slug(base, existing_slugs)
                existing_slugs.add(slug)
                if incoming_slug:
                    report.slug_map[incoming_slug] = slug
                report.created += 1
                if not self.dry_run:
                    await self._create(name, slug, raw, fields, validation_rules)
            except Exception as exc:
                report.failed += 1
                report.errors.append(str(exc))

        return report

    async def _create(
        self,
        name: str,
        slug: str,
        raw: dict[str, Any],
        fields: dict | None,
        validation_rules: list[dict],
    ) -> None:
        now = datetime.now(UTC)
        created = await self.document_type_repository.create(
            DocumentType(
                uuid=uuid4(),
                tenant_id=self.tenant_id,
                workflow_id=self.workflow_id,
                name=name,
                slug=slug,
                description=raw.get("description"),
                keywords=list(raw.get("keywords") or []),
                examples=list(raw.get("examples") or []),
                fields=fields,
                validation_rules=validation_rules,
                current_version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await self.document_type_repository.add_version(
            DocumentTypeVersion(
                document_type_id=created.uuid,
                version=1,
                fields=created.fields,
                validation_rules=created.validation_rules,
            )
        )

    async def _overwrite(
        self,
        match: DocumentType,
        name: str,
        raw: dict[str, Any],
        fields: dict | None,
        validation_rules: list[dict],
    ) -> None:
        schema_changed = match.fields != fields or list(match.validation_rules or []) != validation_rules
        next_version = match.current_version or 1
        if schema_changed:
            latest = await self.document_type_repository.latest_version(match.uuid)
            next_version = (latest.version if latest else (match.current_version or 0)) + 1

        match.name = name
        match.description = raw.get("description")
        match.keywords = list(raw.get("keywords") or [])
        match.examples = list(raw.get("examples") or [])
        match.fields = fields
        match.validation_rules = validation_rules
        match.current_version = next_version
        match.updated_at = datetime.now(UTC)
        await self.document_type_repository.update(match)

        if schema_changed:
            await self.document_type_repository.add_version(
                DocumentTypeVersion(
                    document_type_id=match.uuid,
                    version=next_version,
                    fields=fields,
                    validation_rules=validation_rules,
                )
            )
