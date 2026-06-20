from dataclasses import dataclass
from uuid import UUID

from src.common.application.helpers.webhooks.signing import generate_webhook_secret
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.workflows.domain.repositories.workflow import WorkflowRepository


@dataclass
class WorkflowUpdater(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    name: str | None = None
    selected_doc_types: list | None = None
    kb_document_ids: list | None = None
    per_doc_kb_ids: dict | None = None
    structuring_model: str | None = None
    llm_model: str | None = None
    webhook_url: str | None = None
    webhook_enabled: bool | None = None
    webhook_secret: str | None = None
    webhook_events: list | None = None
    case_noun: dict | None = None

    async def execute(self) -> Workflow:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))

        if self.name is not None:
            workflow.name = self.name
        if self.selected_doc_types is not None:
            workflow.selected_doc_types = self.selected_doc_types
        if self.kb_document_ids is not None:
            workflow.kb_document_ids = self.kb_document_ids
        if self.per_doc_kb_ids is not None:
            workflow.per_doc_kb_ids = self.per_doc_kb_ids
        if self.structuring_model is not None:
            workflow.structuring_model = self.structuring_model
        if self.llm_model is not None:
            workflow.llm_model = self.llm_model
        if self.webhook_url is not None:
            workflow.webhook_url = self.webhook_url
        if self.webhook_enabled is not None:
            workflow.webhook_enabled = self.webhook_enabled
        if self.webhook_secret is not None:
            workflow.webhook_secret = self.webhook_secret
        if self.webhook_events is not None:
            workflow.webhook_events = self.webhook_events
        if self.case_noun is not None:
            workflow.case_noun = self.case_noun

        # Auto-provision a signing secret the first time webhooks are enabled (§6).
        if workflow.webhook_enabled and not workflow.webhook_secret:
            workflow.webhook_secret = generate_webhook_secret()

        return await self.workflow_repository.update(workflow)
