from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.workflow_member import WorkflowMember, WorkflowPermissions


@dataclass
class WorkflowMemberPresenter(Presenter[WorkflowMember]):
    instance: WorkflowMember

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "user_id": str(self.instance.user_id),
            "name": self.instance.full_name,
            "email": self.instance.email,
            "role": self.instance.role,
            "photo": self.instance.photo,
            "is_owner": self.instance.is_owner,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }


@dataclass
class WorkflowPermissionsPresenter(Presenter[WorkflowPermissions]):
    instance: WorkflowPermissions

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": str(self.instance.workflow_id),
            "access_type": self.instance.access_type,
            "members": [WorkflowMemberPresenter(instance=m).to_dict for m in self.instance.members],
        }


@dataclass
class AssignableUserPresenter(Presenter[TenantUser]):
    """A tenant member shown in the add-member picker."""

    instance: TenantUser

    @property
    def to_dict(self) -> dict[str, Any]:
        first = self.instance.display_first_name or ""
        last = self.instance.display_last_name or ""
        email = self.instance.email_address.email if self.instance.email_address else None
        name = f"{first} {last}".strip() or (email or "")
        return {
            "user_id": str(self.instance.user_id),
            "tenant_user_id": str(self.instance.uuid),
            "name": name,
            "email": email,
            "photo": self.instance.photo,
            "is_owner": self.instance.is_owner,
        }
