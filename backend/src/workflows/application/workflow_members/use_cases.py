"""Use cases for workflow permissions (access type + explicit members).

A workflow is either ``organization`` (every tenant member may access it) or
``private`` (only the tenant owner, the workflow creator and explicit members
may access it). ``EnsureWorkflowAccess`` is the shared guard reused across the
workflow + sub-resource endpoints; the rest power the permissions page.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import (
    WorkflowAccessDeniedError,
    WorkflowMemberAlreadyExistsError,
    WorkflowMemberNotFoundError,
    WorkflowNotFoundError,
)
from src.common.domain.exceptions.users import TenantUserNotFoundError
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow, WorkflowAccessType
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.workflow_member import (
    WorkflowMember,
    WorkflowMemberRole,
    WorkflowPermissions,
)
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository


@dataclass
class EnsureWorkflowAccess(UseCase):
    """Authorize ``tenant_user`` for ``workflow_id`` or raise 403/404.

    Organization workflows are open to every tenant member (tenant-level
    permissions are checked separately). Private workflows are restricted to the
    tenant owner, the creator and explicit members.
    """

    workflow_id: UUID
    tenant_id: UUID
    tenant_user: TenantUser
    workflow_repository: WorkflowRepository
    member_repository: WorkflowMemberRepository

    async def execute(self) -> Workflow:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        if workflow.access_type != "private":
            return workflow
        if self.tenant_user.is_owner:
            return workflow
        if workflow.created_by_id is not None and workflow.created_by_id == self.tenant_user.user_id:
            return workflow
        member = await self.member_repository.find(
            self.workflow_id, self.tenant_user.user_id, self.tenant_id
        )
        if member is None:
            raise WorkflowAccessDeniedError(str(self.workflow_id))
        return workflow


@dataclass
class GetWorkflowPermissions(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    member_repository: WorkflowMemberRepository

    async def execute(self) -> WorkflowPermissions:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        members = await self.member_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        return WorkflowPermissions(
            workflow_id=self.workflow_id,
            access_type=workflow.access_type,
            members=members,
        )


@dataclass
class SetWorkflowAccessType(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    access_type: WorkflowAccessType
    workflow_repository: WorkflowRepository
    member_repository: WorkflowMemberRepository

    async def execute(self) -> WorkflowPermissions:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        workflow.access_type = self.access_type
        await self.workflow_repository.update(workflow)
        members = await self.member_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        return WorkflowPermissions(
            workflow_id=self.workflow_id,
            access_type=workflow.access_type,
            members=members,
        )


@dataclass
class AddWorkflowMember(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: WorkflowMemberRole
    workflow_repository: WorkflowRepository
    member_repository: WorkflowMemberRepository
    tenant_user_repository: TenantUserRepository

    async def execute(self) -> WorkflowMember:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        # The user must belong to this tenant before they can be added.
        tenant_user = await self.tenant_user_repository.find_by_args(
            user_id=self.user_id, tenant_id=self.tenant_id
        )
        if tenant_user is None:
            raise TenantUserNotFoundError
        existing = await self.member_repository.find(self.workflow_id, self.user_id, self.tenant_id)
        if existing is not None:
            raise WorkflowMemberAlreadyExistsError(str(self.user_id))
        member = WorkflowMember(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            user_id=self.user_id,
            role=self.role,
        )
        return await self.member_repository.add(member)


@dataclass
class UpdateWorkflowMemberRole(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: WorkflowMemberRole
    member_repository: WorkflowMemberRepository

    async def execute(self) -> WorkflowMember:
        return await self.member_repository.update_role(
            self.workflow_id, self.user_id, self.tenant_id, self.role
        )


@dataclass
class RemoveWorkflowMember(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    user_id: UUID
    member_repository: WorkflowMemberRepository

    async def execute(self) -> None:
        existing = await self.member_repository.find(self.workflow_id, self.user_id, self.tenant_id)
        if existing is None:
            raise WorkflowMemberNotFoundError(str(self.user_id))
        await self.member_repository.remove(self.workflow_id, self.user_id, self.tenant_id)


@dataclass
class ListAssignableUsers(UseCase):
    """Tenant members not already on the workflow (the add-member picker)."""

    workflow_id: UUID
    tenant_id: UUID
    member_repository: WorkflowMemberRepository
    tenant_user_repository: TenantUserRepository

    async def execute(self) -> list[TenantUser]:
        members = await self.member_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        member_user_ids = {member.user_id for member in members}
        tenant_users = await self.tenant_user_repository.filter(
            TenantUserFilters(tenant_ids=[self.tenant_id])
        )
        return [
            tenant_user
            for tenant_user in tenant_users
            if tenant_user.is_active and tenant_user.user_id not in member_user_ids
        ]
