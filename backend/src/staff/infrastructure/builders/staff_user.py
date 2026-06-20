from src.common.database.models.staff_user import StaffUserORM
from src.staff.domain.models.staff_user import StaffRole, StaffUser, StaffUserStatus


def build_staff_user(orm_instance: StaffUserORM) -> StaffUser:
    return StaffUser(
        uuid=orm_instance.uuid,
        user_id=orm_instance.user_id,
        role=StaffRole(orm_instance.role),
        status=StaffUserStatus(orm_instance.status),
        created_at=orm_instance.created_at,
        revoked_at=orm_instance.revoked_at,
    )
