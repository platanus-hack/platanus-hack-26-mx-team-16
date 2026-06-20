from src.common.database.models.workflow_member import WorkflowMemberORM
from src.common.domain.models.workflow_member import WorkflowMember


def build_workflow_member(
    orm_instance: WorkflowMemberORM,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    photo: str | None = None,
    is_owner: bool = False,
) -> WorkflowMember:
    """Map a ``WorkflowMemberORM`` row to the domain model.

    Profile fields (``first_name`` / ``email`` / ...) are supplied by the caller
    from the member's tenant-user record; they are never stored on the row.
    """
    return WorkflowMember(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        user_id=orm_instance.user_id,
        role=orm_instance.role,
        first_name=first_name,
        last_name=last_name,
        email=email,
        photo=photo,
        is_owner=is_owner,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
