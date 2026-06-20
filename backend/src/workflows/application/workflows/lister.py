from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository


@dataclass
class WorkflowsLister(UseCase):
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    industry_id: UUID | None = None
    # When provided, private workflows the user cannot access are filtered out.
    member_repository: WorkflowMemberRepository | None = None
    tenant_user: TenantUser | None = None

    async def execute(self) -> list[Workflow]:
        workflows = await self.workflow_repository.list_by_tenant(self.tenant_id, self.industry_id)

        if self.tenant_user is None or self.member_repository is None or self.tenant_user.is_owner:
            return workflows

        member_workflow_ids = set(
            await self.member_repository.list_workflow_ids_for_user(
                self.tenant_user.user_id, self.tenant_id
            )
        )
        return [
            workflow
            for workflow in workflows
            if workflow.access_type != "private"
            or workflow.created_by_id == self.tenant_user.user_id
            or workflow.uuid in member_workflow_ids
        ]
