"""Duplicar workflow (deep-copy) — ADR 0002 · §3.7.

Reúso = duplicar, no compartir: crea un workflow NUEVO (copy-on-create le da su
pipeline propio v1) y le importa **en memoria** el bundle del origen ⇒ el importer
appendea una v2 a SU pipeline y materializa doctypes + reglas + KB refs. Cero
referencias compartidas — el escenario del BUG 3 es imposible por construcción.

Alcance (zanjado #7): doctypes + reglas + pipeline/policies + KB refs por slug +
config del workflow. Excluye documentos/casos, sources/destinations (secretos ⇒
``requiresConfiguration``) y miembros. El duplicado nace ``organization`` (no
hereda ``access_type`` privado ni miembros).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.application.workflows.creator import WorkflowCreator
from src.workflows.application.workflows.import_export.exporter import (
    WorkflowBundleExporter,
)
from src.workflows.application.workflows.import_export.importer import (
    ImportConflictStrategy,
    WorkflowBundleImporter,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.tool import ToolRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository

# Config del workflow que el duplicado hereda más allá de lo que ya copia el
# creator. Excluye secretos/relaciones: ``webhook_*`` (destino), ``access_type``
# (el duplicado nace 'organization'), miembros, docs/casos, sources/destinations.
_COPIED_CONFIG_FIELDS = (
    "output_schema",
    "synthesis_template",
    "synthesis_enabled",
    "analysis_reviewer_model",
    "analysis_critic_model",
    "analysis_consensus_samples",
    "case_noun",
)


@dataclass
class DuplicateWorkflow(UseCase):
    source_workflow_id: UUID
    tenant_id: UUID
    new_name: str
    workflow_repository: WorkflowRepository
    pipeline_repository: PipelineRepository
    rule_repository: WorkflowRuleRepository
    document_type_repository: DocumentTypeRepository
    kb_document_repository: KBDocumentRepository
    # Tools workflow-scoped (2026-06): el duplicado recibe su propia copia; la
    # credencial (ConnectionAccount org) se comparte por referencia, sin secretos.
    tool_repository: ToolRepository | None = None
    created_by_id: UUID | None = None
    # ids de reglas materializadas ⇒ el endpoint programa su recompilación.
    rule_ids_to_recompile: list[UUID] = field(default_factory=list)

    async def execute(self) -> Workflow:
        source = await self.workflow_repository.find_by_id(self.source_workflow_id, self.tenant_id)
        if source is None:
            raise WorkflowNotFoundError(str(self.source_workflow_id))

        # 1. Bundle del origen (doctypes + reglas + pipeline + KB refs; excluye
        #    sources/destinations vía requiresConfiguration).
        bundle = await WorkflowBundleExporter(
            workflow_id=self.source_workflow_id,
            tenant_id=self.tenant_id,
            workflow_repository=self.workflow_repository,
            pipeline_repository=self.pipeline_repository,
            rule_repository=self.rule_repository,
            document_type_repository=self.document_type_repository,
            kb_document_repository=self.kb_document_repository,
        ).execute()

        # 2. Workflow nuevo (copy-on-create ⇒ pipeline propio v1) + config heredada.
        new_workflow = await WorkflowCreator(
            tenant_id=self.tenant_id,
            name=self.new_name,
            # E7 · F2: el pipeline real se hereda al importar el bundle del origen
            # (paso 3); el creator solo siembra el default antes del import.
            industry_id=source.industry_id,
            selected_doc_types=list(source.selected_doc_types or []),
            kb_document_ids=list(source.kb_document_ids or []),
            per_doc_kb_ids=dict(source.per_doc_kb_ids or {}),
            structuring_model=source.structuring_model,
            llm_model=source.llm_model,
            created_by_id=self.created_by_id,
            workflow_repository=self.workflow_repository,
            pipeline_repository=self.pipeline_repository,
        ).execute()

        for field_name in _COPIED_CONFIG_FIELDS:
            setattr(new_workflow, field_name, getattr(source, field_name))
        new_workflow = await self.workflow_repository.update(new_workflow)

        # 3. Importar el bundle en el workflow nuevo ⇒ appendea v2 a SU pipeline,
        #    materializa doctypes + reglas + KB refs (todo privado del duplicado).
        importer = WorkflowBundleImporter(
            workflow_id=new_workflow.uuid,
            tenant_id=self.tenant_id,
            payload=bundle,
            strategy=ImportConflictStrategy.OVERWRITE,
            workflow_repository=self.workflow_repository,
            pipeline_repository=self.pipeline_repository,
            rule_repository=self.rule_repository,
            document_type_repository=self.document_type_repository,
            kb_document_repository=self.kb_document_repository,
            dry_run=False,
        )
        await importer.execute()
        self.rule_ids_to_recompile = importer.rule_ids_to_recompile or []

        # 4. Tools del workflow (fuera del bundle: config no-secreta que apunta a
        #    la ConnectionAccount org, válida tenant-wide).
        if self.tool_repository is not None:
            for tool in await self.tool_repository.list_by_workflow(
                self.source_workflow_id, self.tenant_id
            ):
                await self.tool_repository.upsert(
                    tool.model_copy(
                        update={"uuid": uuid4(), "workflow_id": new_workflow.uuid}
                    )
                )

        # Re-leer para devolver el estado final (pipeline_id/slug ya bindeados).
        refreshed = await self.workflow_repository.find_by_id(new_workflow.uuid, self.tenant_id)
        return refreshed or new_workflow
