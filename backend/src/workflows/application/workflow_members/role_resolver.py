"""Resolución del rol efectivo de un tenant user sobre un workflow (E5 · §5).

Reglas (diseño E5, sin re-litigar):
- tenant owner/admin ⇒ ``admin``.
- miembro explícito ⇒ su rol (también en workflows ``organization`` — antes el
  member solo se consultaba en ``private``).
- creador del workflow ⇒ ``admin`` (paridad con ``EnsureWorkflowAccess``, que
  ya le da acceso a su workflow private aunque no tenga fila de member).
- workflow ``organization`` sin fila ⇒ ``member`` implícito (no-regresión).
- workflow ``private`` sin fila ⇒ ``None`` = sin acceso.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository


def is_tenant_admin(tenant_user: TenantUser) -> bool:
    """Owner del tenant o rol tenant ``admin`` ⇒ admin en TODOS los workflows."""
    if tenant_user.is_owner:
        return True
    return tenant_user.tenant_role is not None and tenant_user.tenant_role.slug == "admin"


@dataclass
class ResolveWorkflowRole(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    tenant_user: TenantUser
    workflow_repository: WorkflowRepository
    member_repository: WorkflowMemberRepository

    async def execute(self) -> str | None:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        if is_tenant_admin(self.tenant_user):
            return "admin"
        member = await self.member_repository.find(
            self.workflow_id, self.tenant_user.user_id, self.tenant_id
        )
        if member is not None:
            return member.role
        if workflow.created_by_id is not None and workflow.created_by_id == self.tenant_user.user_id:
            return "admin"
        if workflow.access_type != "private":
            return "member"
        return None
