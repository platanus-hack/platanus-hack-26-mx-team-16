"""Export a whole workflow as a git-able bundle envelope (E6 · W4 · diseño §4).

Composes the existing rules exporter, the new doc-types exporter, and the
workflow's current pipeline version into one declarative, secret-free envelope.
Sources/destinations/connections are intentionally excluded (secrets,
environment-specific) and surfaced as ``requiresConfiguration`` so the importer
side knows what still needs wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.application.document_types.import_export.exporter import (
    WorkflowDocumentTypesExporter,
)
from src.workflows.application.workflow_rules.import_export.exporter import (
    WorkflowRulesExporter,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository

BUNDLE_SCHEMA_VERSION = "1.0"

# Secciones ambiente-specific (secrets) que el bundle NO transporta.
REQUIRES_CONFIGURATION = ["destinations", "sources"]


@dataclass
class WorkflowBundleExporter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    pipeline_repository: PipelineRepository
    rule_repository: WorkflowRuleRepository
    document_type_repository: DocumentTypeRepository
    kb_document_repository: KBDocumentRepository

    async def execute(self) -> dict[str, Any]:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))

        document_types = await WorkflowDocumentTypesExporter(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            document_type_repository=self.document_type_repository,
        ).execute()

        rules_envelope = await WorkflowRulesExporter(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            rule_repository=self.rule_repository,
            document_type_repository=self.document_type_repository,
            kb_document_repository=self.kb_document_repository,
        ).execute()

        pipeline_section = await self._export_pipeline(workflow.pipeline_id)

        return {
            "schemaVersion": BUNDLE_SCHEMA_VERSION,
            "kind": "workflow_bundle",
            "exportedAt": datetime.now(UTC).isoformat(),
            "workflow": {
                "name": workflow.name,
                "slug": workflow.slug,
                # E7 · F2: `workflowType` retirado del envelope (el pipeline section
                # ya lleva kind + fases — la receta es la fuente de verdad).
                "outputSchema": workflow.output_schema,
                # Sustantivo del caso (es/en · one/other) o null. No-secreto, viaja
                # en el bundle (product/specs/data-model/case-noun.md §3.6).
                "caseNoun": workflow.case_noun,
            },
            "documentTypes": document_types,
            "rules": rules_envelope.get("rules", []),
            "pipeline": pipeline_section,
            "requiresConfiguration": list(REQUIRES_CONFIGURATION),
        }

    async def _export_pipeline(self, pipeline_id: UUID | None) -> dict[str, Any] | None:
        if pipeline_id is None:
            return None
        pipeline = await self.pipeline_repository.find_by_id(pipeline_id, self.tenant_id)
        if pipeline is None:
            return None
        version = None
        if pipeline.current_version is not None:
            version = await self.pipeline_repository.get_version(pipeline.uuid, pipeline.current_version)
        if version is None:
            version = await self.pipeline_repository.latest_version(pipeline.uuid)
        if version is None:
            return {
                "slug": pipeline.slug,
                "name": pipeline.name,
                "kind": pipeline.kind.value,
                "phases": [],
                "outputSchema": None,
            }
        return {
            "slug": pipeline.slug,
            "name": pipeline.name,
            "kind": pipeline.kind.value,
            "phases": [p.model_dump(mode="json") for p in version.phases],
            "outputSchema": version.output_schema,
        }
