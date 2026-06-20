from src.common.database.models.case_event import CaseEventORM
from src.workflows.domain.models.case_event import CaseEvent


def build_case_event(orm: CaseEventORM) -> CaseEvent:
    return CaseEvent(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        case_id=orm.case_id,
        type=orm.type,
        payload=orm.payload or {},
        actor=orm.actor,
        dedupe_key=orm.dedupe_key,
        created_at=orm.created_at,
    )
