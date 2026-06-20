from dataclasses import dataclass
from uuid import UUID

from src.common.application.helpers.webhooks.signing import generate_webhook_secret
from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.domain.repositories.workflow import WorkflowRepository


@dataclass
class WorkflowWebhookSecretRegenerator(UseCase):
    """Regenerate the per-workflow webhook signing secret (spec §4.9)."""

    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository

    async def execute(self) -> Workflow:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))
        workflow.webhook_secret = generate_webhook_secret()
        return await self.workflow_repository.update(workflow)
