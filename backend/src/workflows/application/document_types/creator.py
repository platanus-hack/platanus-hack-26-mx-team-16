from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)
from src.workflows.domain.services.json_schema_validator import validate_document_type_json_schema
from src.workflows.domain.services.validation_rules_validator import (
    validate_document_type_validation_rules,
)


@dataclass
class DocumentTypeCreator(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    name: str
    document_type_repository: DocumentTypeRepository
    workflow_repository: WorkflowRepository
    description: str | None = None
    is_shareable: bool = False
    fields: dict | None = None
    validation_rules: list[dict] | None = None

    async def execute(self) -> DocumentType:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))

        if self.fields is not None:
            validate_document_type_json_schema(self.fields)

        validation_rules = (
            validate_document_type_validation_rules(self.validation_rules) if self.validation_rules is not None else []
        )

        existing_slugs = await self.document_type_repository.list_slugs_by_workflow(self.workflow_id, self.tenant_id)
        slug = compute_unique_slug(slugify_doctype_name(self.name), existing_slugs)

        now = datetime.now(UTC)
        document_type = DocumentType(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=self.name,
            is_shareable=self.is_shareable,
            slug=slug,
            description=self.description,
            fields=self.fields,
            validation_rules=validation_rules,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        created = await self.document_type_repository.create(document_type)

        # Toda nueva versión del contrato es inmutable (D6'): el doc type nace
        # con v1 sellada para que el sellado por run siempre tenga versión.
        await self.document_type_repository.add_version(
            DocumentTypeVersion(
                document_type_id=created.uuid,
                version=1,
                fields=created.fields,
                validation_rules=created.validation_rules,
            )
        )
        return created
