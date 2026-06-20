from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.enums.pipelines import PipelineStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion
from src.workflows.domain.recipes import pipeline_template_for_slug
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository


@dataclass
class WorkflowCreator(UseCase):
    tenant_id: UUID
    name: str
    workflow_repository: WorkflowRepository
    # E7 · F2: `workflow_type` murió. El alta elige una PLANTILLA por slug
    # (recipes.pipeline_template_for_slug); None ⇒ extracción estándar (default).
    template_slug: str | None = None
    selected_doc_types: list = field(default_factory=list)
    kb_document_ids: list = field(default_factory=list)
    per_doc_kb_ids: dict = field(default_factory=dict)
    industry_id: UUID | None = None
    structuring_model: str | None = None
    llm_model: str | None = None
    created_by_id: UUID | None = None
    # ADR 0002 · copy-on-create: el workflow nace dueño de su pipeline propio,
    # clonado de la plantilla elegida en el alta (``template_slug``). Sin repo de
    # pipelines (algunos tests) el workflow queda sin pipeline y un run da 409.
    pipeline_repository: PipelineRepository | None = None

    async def execute(self) -> Workflow:
        now = datetime.now(UTC)
        workflow = Workflow(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            industry_id=self.industry_id,
            pipeline_id=None,
            name=self.name,
            selected_doc_types=self.selected_doc_types,
            kb_document_ids=self.kb_document_ids,
            per_doc_kb_ids=self.per_doc_kb_ids,
            structuring_model=self.structuring_model,
            llm_model=self.llm_model,
            created_by_id=self.created_by_id,
            created_at=now,
            updated_at=now,
        )
        workflow = await self.workflow_repository.create(workflow)

        if self.pipeline_repository is not None:
            workflow = await self._provision_pipeline(workflow)

        return workflow

    async def _provision_pipeline(self, workflow: Workflow) -> Workflow:
        """Clone the chosen template into the workflow's own pipeline (ADR 0002)."""
        template = pipeline_template_for_slug(self.template_slug)
        base_slug = workflow.slug or f"wf-{workflow.uuid.hex[:8]}"
        pipeline = await self.pipeline_repository.upsert(
            Pipeline(
                uuid=uuid4(),
                workflow_id=workflow.uuid,
                tenant_id=self.tenant_id,
                slug=f"{base_slug}-pipeline",
                name=template.name,
                kind=template.kind,
                status=PipelineStatus.ACTIVE,
                current_version=1,
            )
        )
        await self.pipeline_repository.add_version(
            PipelineVersion(
                uuid=uuid4(),
                pipeline_id=pipeline.uuid,
                version=1,
                phases=template.phases,
            )
        )
        workflow.pipeline_id = pipeline.uuid
        # El alta siembra el sustantivo del caso de la plantilla (None ⇒ la UI
        # cae al default «Caso/Casos»). product/specs/data-model/case-noun.md §3.4.
        workflow.case_noun = template.case_noun
        return await self.workflow_repository.update(workflow)
