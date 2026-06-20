from src.common.database.models.human_task import HumanTaskORM
from src.common.domain.enums.human_tasks import (
    HumanTaskAssigneeMode,
    HumanTaskKind,
    HumanTaskStatus,
)
from src.workflows.domain.models.human_task import HumanTask


def build_human_task(orm: HumanTaskORM) -> HumanTask:
    return HumanTask(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        task_key=orm.task_key,
        kind=HumanTaskKind(orm.kind),
        status=HumanTaskStatus(orm.status),
        assignee_mode=HumanTaskAssigneeMode(orm.assignee_mode),
        audience=orm.audience,
        workflow_id=orm.workflow_id,
        case_id=orm.case_id,
        pipeline_run_id=orm.pipeline_run_id,
        payload=orm.payload,
        resolution=orm.resolution,
        expires_at=orm.expires_at,
        stage=orm.stage,
        claimed_by=orm.claimed_by,
        claimed_at=orm.claimed_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
