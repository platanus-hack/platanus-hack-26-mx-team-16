"""Update a document type (D6' · E2 — workflow-scoped versioning).

Versioning contract:

- An **effective change to the extraction contract** — ``fields`` or
  ``validation_rules``, including ``clear_fields`` and the reset performed
  when a new ``sample_file_id`` arrives — appends an immutable row to
  ``document_type_versions`` and bumps ``current_version``. The JSONB on
  ``document_types`` keeps being the "current" truth so existing readers
  don't change; versions are the sealed history runs pin at dispatch time.
- Identity/classification-only edits (``name``, ``description``,
  ``keywords``, ``examples``, ``is_shareable``) do NOT create a version.
- The slug is **stable after creation** (same decision as
  ``WorkflowRule.slug``): renaming no longer regenerates it, so compiled
  ``@slug`` references in workflow rules keep resolving. It is only computed
  here for legacy rows that predate the slug backfill (slug is None).

Callers that need to react to a new version (e.g. invalidate rule
compilations) get ``DocumentTypeUpdateOutcome.created_new_version``.
"""

import json
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)
from src.workflows.domain.services.json_schema_validator import validate_document_type_json_schema
from src.workflows.domain.services.validation_rules_validator import (
    validate_document_type_validation_rules,
)


def _contract_snapshot(document_type: DocumentType) -> str:
    """Canonical dump of the version-triggering surface (fields + validations)."""
    return json.dumps(
        {
            "fields": document_type.fields,
            "validation_rules": document_type.validation_rules,
        },
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )


@dataclass
class DocumentTypeUpdateOutcome:
    document_type: DocumentType
    created_new_version: bool = False
    new_version: int | None = None


@dataclass
class DocumentTypeUpdater(UseCase):
    document_type_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository
    name: str | None = None
    description: str | None = None
    is_shareable: bool | None = None
    fields: dict | None = None
    clear_fields: bool = False
    keywords: list[str] | None = None
    examples: list[str] | None = None
    validation_rules: list[dict] | None = None
    sample_file_id: "UUID | None" = None

    async def execute(self) -> DocumentTypeUpdateOutcome:
        document_type = await self.document_type_repository.find_by_id(self.document_type_id, self.tenant_id)
        if not document_type:
            raise DocumentTypeNotFoundError(str(self.document_type_id))

        if self.name is not None and self.name != document_type.name:
            # Slug deliberately untouched: stable after creation (see module
            # docstring) so @slug refs in compiled rules survive renames.
            document_type.name = self.name
        if document_type.slug is None:
            document_type.slug = await self._compute_missing_slug(document_type.workflow_id, document_type.name)

        contract_before = _contract_snapshot(document_type)

        if self.description is not None:
            document_type.description = self.description
        if self.is_shareable is not None:
            document_type.is_shareable = self.is_shareable
        if self.clear_fields:
            document_type.fields = None
        elif self.fields is not None:
            validate_document_type_json_schema(self.fields)
            document_type.fields = self.fields
        if self.keywords is not None:
            document_type.keywords = self.keywords
        if self.examples is not None:
            document_type.examples = self.examples
        if self.validation_rules is not None:
            document_type.validation_rules = validate_document_type_validation_rules(self.validation_rules)
        if self.sample_file_id is not None:
            self._apply_sample_file(document_type)

        created_new_version = _contract_snapshot(document_type) != contract_before
        if created_new_version:
            new_version = (document_type.current_version or 0) + 1
            await self.document_type_repository.add_version(
                DocumentTypeVersion(
                    document_type_id=document_type.uuid,
                    version=new_version,
                    fields=document_type.fields,
                    validation_rules=document_type.validation_rules,
                )
            )
            document_type.current_version = new_version

        updated = await self.document_type_repository.update(document_type)
        return DocumentTypeUpdateOutcome(
            document_type=updated,
            created_new_version=created_new_version,
            new_version=document_type.current_version if created_new_version else None,
        )

    def _apply_sample_file(self, document_type: DocumentType) -> None:
        if document_type.sample_file_id == self.sample_file_id:
            document_type.sample_file_id = self.sample_file_id
            return
        if self.fields is None:
            document_type.fields = None
        document_type.sample_file_text = None
        document_type.sample_file_id = self.sample_file_id

    async def _compute_missing_slug(self, workflow_id: UUID, name: str) -> str:
        existing = await self.document_type_repository.list_slugs_by_workflow(
            workflow_id,
            self.tenant_id,
            exclude_document_type_id=self.document_type_id,
        )
        return compute_unique_slug(slugify_doctype_name(name), existing)
