from src.common.database.models.staff_access_event import StaffAccessEventORM
from src.staff.domain.models.staff_access_event import StaffAccessEvent


def build_staff_access_event(orm_instance: StaffAccessEventORM) -> StaffAccessEvent:
    return StaffAccessEvent(
        uuid=orm_instance.uuid,
        staff_user_id=orm_instance.staff_user_id,
        action=orm_instance.action,
        tenant_id=orm_instance.tenant_id,
        case_id=orm_instance.case_id,
        task_id=orm_instance.task_id,
        request_id=orm_instance.request_id,
        ip=orm_instance.ip,
        # Columna `metadata` ↔ atributo ORM `event_metadata` (reservado SQLAlchemy).
        metadata=orm_instance.event_metadata or {},
        created_at=orm_instance.created_at,
    )
